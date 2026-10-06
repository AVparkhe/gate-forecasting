import argparse
import sys
import logging
from pathlib import Path
import uuid
import sqlite3
from datetime import datetime

# Adjust path to import local modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DB_PATH
from pipeline.target_builder import TargetBuilder
from pipeline.time_series import TimeSeriesBuilder
from pipeline.feature_engineering import FeatureEngineer
from pipeline.baseline_models import BaselineModels
from pipeline.forecasting_models import ForecastingModels
from pipeline.ranking import RankingEngine
from pipeline.evaluation import Evaluator

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_backtest(db_path: Path, start_year: int, end_year: int, level: str, model_type: str):
    logger.info(f"Starting Walk-Forward Backtest for {level} level ({start_year}-{end_year}) using {model_type}")
    
    run_id = f"backtest_{model_type}_{level}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 1. Build Full Targets
    builder = TargetBuilder(db_path)
    full_matrices = builder.build_matrices(level)
    
    if full_matrices["appearance"].empty:
        logger.error(f"No enriched data found for level {level}. Have you run Phase 3?")
        return
        
    ts_builder = TimeSeriesBuilder(full_matrices)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    all_metrics = {}
    
    # Walk-forward loop
    for target_year in range(start_year, end_year + 1):
        if target_year not in full_matrices["appearance"].index:
            logger.warning(f"No actual data for {target_year}. Skipping.")
            continue
            
        logger.info(f"Target Year: {target_year}")
        
        # 2. Get safe history (Strict isolation!)
        history = ts_builder.get_history_up_to(target_year)
        if history["appearance"].empty:
            logger.warning(f"No history available before {target_year}. Skipping.")
            continue
            
        train_start = history["appearance"].index.min()
        train_end = history["appearance"].index.max()
        total_historical_years = len(history["appearance"])
        
        # 3. Feature Engineering
        engineer = FeatureEngineer(history)
        features = engineer.build_features(target_year)
        
        # 4. Predict
        if model_type in ['hist_freq', 'recent_freq', 'ema']:
            if model_type == 'hist_freq':
                raw_preds = BaselineModels.historical_frequency(features, total_historical_years)
            elif model_type == 'recent_freq':
                raw_preds = BaselineModels.recent_frequency(features, window=5)
            elif model_type == 'ema':
                raw_preds = ForecastingModels.ema(history["appearance"], history["marks"], span=5)
        elif model_type in ['xgboost', 'random_forest']:
            # Construct training dataset for walk-forward ML models
            train_X = []
            train_y = []
            
            # Build features for each historical year
            hy_years = history["appearance"].index.tolist()
            for hy in hy_years:
                if hy < train_start + 1: # need some history to build features
                    continue
                sub_history = ts_builder.get_history_up_to(hy)
                if sub_history["appearance"].empty:
                    continue
                sub_features = FeatureEngineer(sub_history).build_features(hy)
                sub_target = full_matrices["appearance"].loc[hy]
                
                for entity in sub_features.index:
                    feat_dict = sub_features.loc[entity].to_dict()
                    train_X.append(feat_dict)
                    train_y.append(sub_target.get(entity, 0))
            
            if not train_X:
                import pandas as pd
                raw_preds = pd.DataFrame(index=features.index)
                raw_preds['probability'] = 0.0
                raw_preds['expected_marks'] = 0.0
                raw_preds['expected_count'] = 0.0
            else:
                import pandas as pd
                X_df = pd.DataFrame(train_X)
                y_series = pd.Series(train_y)
                
                if model_type == 'xgboost':
                    from models.xgboost_forecaster import XGBoostForecaster
                    model = XGBoostForecaster()
                else:
                    from models.random_forest_forecaster import RandomForestForecaster
                    model = RandomForestForecaster()
                    
                model.train(X_df, y_series)
                raw_preds = model.predict(features)
        else:
            raise ValueError(f"Unknown model: {model_type}")
            
        # 5. Rank
        ranked = RankingEngine.rank_predictions(raw_preds)
        
        # 6. Actuals for evaluation
        actual_app = full_matrices["appearance"].loc[target_year]
        actual_marks = full_matrices["marks"].loc[target_year]
        actual_count = full_matrices["count"].loc[target_year]
        
        # 7. Evaluate
        metrics = Evaluator.evaluate(ranked, actual_app, actual_marks)
        all_metrics[target_year] = metrics
        
        # 8. Store in DB and error analysis
        for entity, row in ranked.iterrows():
            app = actual_app.get(entity, 0)
            marks = actual_marks.get(entity, 0.0)
            count = actual_count.get(entity, 0)
            
            # Error analysis
            error_type = ""
            error_reason = ""
            is_predicted = row['probability'] > 0.5
            
            if is_predicted and not app:
                error_type = "FALSE_POSITIVE"
                error_reason = f"High predicted prob ({row['probability']:.2f}) but didn't appear."
            elif not is_predicted and app:
                error_type = "FALSE_NEGATIVE"
                error_reason = f"Low predicted prob ({row['probability']:.2f}) but appeared."
            
            prediction_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO forecast_predictions (
                    prediction_id, run_id, target_year, level, entity_name,
                    predicted_probability, predicted_question_count, predicted_marks,
                    predicted_rank, confidence_tier, model_name, model_version,
                    feature_version, training_start_year, training_end_year,
                    actual_appearance, actual_question_count, actual_marks,
                    error_type, error_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prediction_id, run_id, target_year, level, str(entity),
                row['probability'], row['expected_count'], row['expected_marks'],
                row['predicted_rank'], row['confidence_tier'], model_type, 'v1',
                'v1', int(train_start), int(train_end),
                bool(app), int(count), float(marks), error_type, error_reason
            ))
            
        conn.commit()
        
    conn.close()
    
    # Summary Report
    logger.info("================================================")
    logger.info(f"BACKTEST SUMMARY ({start_year}-{end_year}) - {model_type.upper()}")
    logger.info("================================================")
    
    avg_metrics = {}
    for k in all_metrics[list(all_metrics.keys())[0]].keys():
        vals = [m[k] for m in all_metrics.values()]
        avg = sum(vals) / len(vals) if vals else 0
        avg_metrics[k] = avg
        
    for k, v in avg_metrics.items():
        logger.info(f"{k}: {v:.3f}")
        
    logger.info(f"Run ID: {run_id}")
    logger.info("================================================")
    
    return avg_metrics
    
def main():
    parser = argparse.ArgumentParser(description="Run Walk-Forward Forecasting Backtest.")
    parser.add_argument('--backtest', nargs=2, type=int, help="Start and end year (e.g. 2015 2024)", required=True)
    parser.add_argument('--level', type=str, choices=['SUBJECT', 'TOPIC', 'SUBTOPIC', 'CONCEPT'], default='TOPIC')
    parser.add_argument('--model', type=str, choices=['hist_freq', 'recent_freq', 'ema', 'xgboost', 'random_forest'], default='ema')
    
    args = parser.parse_args()
    
    run_backtest(DB_PATH, args.backtest[0], args.backtest[1], args.level, args.model)

if __name__ == "__main__":
    main()
