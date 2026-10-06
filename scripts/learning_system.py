import sqlite3
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class LearningSystem:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def analyze_errors(self, run_id: str) -> dict:
        cursor = self.conn.cursor()
        
        # Count False Positives (Predicted but not matched)
        cursor.execute("SELECT COUNT(*) FROM prediction_matches WHERE run_id = ? AND failure_category = 'FALSE_POSITIVE'", (run_id,))
        false_positives = cursor.fetchone()[0]
        
        # Count False Negatives (Not predicted but appeared)
        cursor.execute("SELECT COUNT(*) FROM prediction_matches WHERE run_id = ? AND failure_category = 'FALSE_NEGATIVE'", (run_id,))
        false_negatives = cursor.fetchone()[0]
        
        logger.info(f"Error Analysis for {run_id}: {false_positives} FP, {false_negatives} FN.")
        
        # Very basic hypothesis generation
        hypothesis = ""
        update = ""
        if false_positives > false_negatives:
            hypothesis = "Model is over-predicting based on raw historical frequency."
            update = "Decrease raw frequency weight; increase semantic gap weight."
        else:
            hypothesis = "Model is too conservative and missing emerging trends."
            update = "Increase recent trend weight."
            
        return {
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'hypothesis': hypothesis,
            'update_proposed': update
        }

    def backtest_hypothesis(self, target_year: int, hypothesis: dict, run_id: str):
        # Mocking a backtest evaluation
        old_f1 = 0.57
        new_f1 = 0.57 + (0.05 if hypothesis['false_positives'] > 10 else -0.02)
        
        status = "ACCEPTED" if new_f1 > old_f1 else "REJECTED"
        
        cursor = self.conn.cursor()
        ledger_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO learning_ledger (
                id, iteration_id, target_year, model_version, strategy_version, 
                failure_description, hypothesis, strategy_update_proposed, 
                before_f1, after_f1, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ledger_id, run_id, target_year, "v0.0_mock", "v0.1_mock" if status=="ACCEPTED" else "v0.0_mock",
            f"{hypothesis['false_positives']} FP", hypothesis['hypothesis'], hypothesis['update_proposed'],
            old_f1, new_f1, status
        ))
        self.conn.commit()
        logger.info(f"Backtest {status}: F1 changed from {old_f1} -> {new_f1}")
        
    def close(self):
        self.conn.close()

if __name__ == "__main__":
    from config.settings import DB_PATH
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python3 learning_system.py <run_id> <target_year>")
        sys.exit(1)
        
    ls = LearningSystem(DB_PATH)
    analysis = ls.analyze_errors(sys.argv[1])
    ls.backtest_hypothesis(int(sys.argv[2]), analysis, sys.argv[1])
    ls.close()
