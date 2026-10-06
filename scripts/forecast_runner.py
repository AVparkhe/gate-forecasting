import sys
import uuid
import logging
from datetime import datetime
from pathlib import Path

# Adjust path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DB_PATH
from scripts.paper_generator import ConstraintBasedPaperGenerator
from scripts.prediction_matcher import PredictionMatcher
import sqlite3
import random

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def run_simulation_loop(target_year: int):
    logger.info(f"--- Starting Historical Simulation for GATE {target_year} ---")
    run_id = f"sim_{target_year}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 1. Generate probabilities (Mocking Phase 5 ML output since pandas/xgboost is missing)
    # We will fetch taxonomy elements from db to mock predictions
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT ai_subject, ai_topic, ai_subtopic FROM question_enrichment WHERE ai_subject IS NOT NULL")
    taxonomy_rows = cursor.fetchall()
    
    mock_predictions = []
    for r in taxonomy_rows:
        mock_predictions.append({
            'subject': r[0],
            'topic': r[1],
            'subtopic': r[2],
            'concept': r[2], # mock concept as subtopic
            'marks': random.choice([1.0, 2.0]),
            'probability': random.uniform(0.1, 0.9)
        })
        
    # Record forecast run
    cursor.execute("""
        INSERT INTO forecast_runs (run_id, target_year, model_version, status, prediction_timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (run_id, target_year, "v0.0_mock", "FROZEN", datetime.now().isoformat()))
    conn.commit()
    
    # 2. Paper Generation
    logger.info("Generating Paper Constraints...")
    generator = ConstraintBasedPaperGenerator(DB_PATH)
    predicted_paper = generator.generate_predicted_paper(mock_predictions, target_year)
    generator.close()
    
    # Store predictions
    for p in predicted_paper:
        cursor.execute("""
            INSERT INTO forecast_predictions (
                run_id, prediction_id, subject, topic, subtopic, concept, 
                marks, probability, confidence, prediction_level, prediction_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, p['prediction_id'], p['subject'], p['topic'], p['subtopic'], p['concept'],
            p['marks'], p['probability'], p['confidence'], "CONCEPT", "MOCK_ENSEMBLE"
        ))
    conn.commit()
    
    # 3. Match against actual paper
    logger.info(f"Revealing Actual {target_year} Paper & Matching...")
    matcher = PredictionMatcher(DB_PATH)
    matcher.compare(run_id, predicted_paper, target_year)
    matcher.close()
    
    # 4. Error Analysis & Learning
    logger.info(f"Executing Error Analysis & Strategy Update...")
    from scripts.learning_system import LearningSystem
    ls = LearningSystem(DB_PATH)
    analysis = ls.analyze_errors(run_id)
    ls.backtest_hypothesis(target_year, analysis, run_id)
    ls.close()
    
    conn.close()
    logger.info(f"--- Simulation Complete for {target_year} ---")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, default=2020)
    args = parser.parse_args()
    run_simulation_loop(args.year)
