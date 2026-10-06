import sys
import json
import logging
from pathlib import Path

# Adjust path to import local modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DB_PATH
from scripts.forecast import run_backtest

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

import sys
import json
import logging
from pathlib import Path

# Adjust path to import local modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DB_PATH
from scripts.forecast import run_backtest
from pipeline.model_selection import ModelSelector
from pipeline.ensemble import EnsembleForecaster

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def run_experiments():
    logger.info("=== Phase 5: Executing ML Walk-Forward Experiments ===")
    start_year = 2015
    end_year = 2024
    level = 'TOPIC'
    
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Run EMA baseline (Experiment 0)
    logger.info("Running Baseline (EMA)...")
    ema_metrics = run_backtest(DB_PATH, start_year, end_year, level, 'ema')
    
    # Run XGBoost (Experiment 1)
    logger.info("Running Experiment 1 (XGBoost)...")
    xgb_metrics = run_backtest(DB_PATH, start_year, end_year, level, 'xgboost')
    
    # Run Random Forest (Experiment 2)
    logger.info("Running Experiment 2 (Random Forest)...")
    rf_metrics = run_backtest(DB_PATH, start_year, end_year, level, 'random_forest')
    
    # Evaluate Models
    selector = ModelSelector(min_f1_improvement=0.01) # e.g. 1% improvement to accept
    logger.info("Evaluating XGBoost against EMA...")
    xgb_accepted = selector.evaluate(xgb_metrics, ema_metrics)
    
    logger.info("Evaluating Random Forest against EMA...")
    rf_accepted = selector.evaluate(rf_metrics, ema_metrics)
    
    results = {
        "experiments": "Phase 5 Evaluation",
        "level": level,
        "backtest_window": f"{start_year}-{end_year}",
        "metrics": {
            "ema": ema_metrics,
            "xgboost": xgb_metrics,
            "random_forest": rf_metrics
        },
        "decisions": {
            "xgboost_accepted": xgb_accepted,
            "random_forest_accepted": rf_accepted
        }
    }
    
    out_file = reports_dir / "phase5_experiments.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=4)
        
    logger.info(f"Froze Phase 5 experiment results to {out_file}")
    
    # Ensembling logic would then follow to produce final forecasts for 2025
    # e.g. using EnsembleForecaster(weights={'ema': 0.4, 'xgboost': 0.6})
    
if __name__ == "__main__":
    run_experiments()
