import argparse
import sys
import logging
import json
from pathlib import Path
from datetime import datetime

# Adjust path to import local modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DB_PATH
from pipeline.db_manager import DatabaseManager
from pipeline.cross_validator import CrossValidator

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

ALGORITHM_VERSION = "v1.0"
CONFIG_VERSION = "v1.0"

def main():
    parser = argparse.ArgumentParser(description="Reconcile Official and GATE Overflow datasets.")
    parser.add_argument('--dry-run', action='store_true', help="Run without saving to DB. Outputs reports.")
    parser.add_argument('--commit', action='store_true', help="Save to golden_questions DB table.")
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.commit:
        logger.error("Must specify either --dry-run or --commit")
        sys.exit(1)
        
    db = DatabaseManager(DB_PATH)
    
    # Generate unique run ID
    run_id = f"run_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}"
    logger.info(f"Starting reconciliation run {run_id}")
    
    # Get all questions
    raw_questions = db.get_all_questions()
    logger.info(f"Fetched {len(raw_questions)} questions from the database.")
    
    # Initialize CrossValidator
    validator = CrossValidator(run_id, ALGORITHM_VERSION, CONFIG_VERSION)
    
    # Run reconciliation
    golden_questions, report, review_queue = validator.reconcile(raw_questions)
    
    logger.info(f"Reconciliation completed.")
    logger.info(f"Generated {len(golden_questions)} golden question records.")
    
    # Print high-level report
    print("\n--- RECONCILIATION REPORT ---")
    print(json.dumps(report, indent=4))
    
    review_dir = Path("data/review")
    review_dir.mkdir(parents=True, exist_ok=True)
    
    if args.dry_run:
        logger.info("DRY RUN: Writing reports to disk...")
        
        with open("reconciliation_report.json", "w") as f:
            json.dump(report, f, indent=4)
            
        with open(review_dir / "uncertain_matches.json", "w") as f:
            json.dump(review_queue, f, indent=4)
            
        logger.info("Dry run complete. No database changes were made.")
        
    if args.commit:
        logger.info("COMMIT: Inserting records into golden_questions table...")
        
        inserted = 0
        for gq in golden_questions:
            db.insert_golden_question(gq)
            inserted += 1
            
        logger.info(f"Successfully inserted {inserted} records into golden_questions.")
        
        # We can also save the review queue so the user can see what needs review even after commit
        with open(review_dir / "uncertain_matches.json", "w") as f:
            json.dump(review_queue, f, indent=4)

if __name__ == "__main__":
    main()
