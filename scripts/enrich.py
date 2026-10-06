import argparse
import sys
import logging
import json
import csv
from pathlib import Path
from datetime import datetime
import os
import uuid

# Load dotenv to get API keys
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Adjust path to import local modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DB_PATH
from pipeline.db_manager import DatabaseManager
from pipeline.llm_interface import get_llm_provider, TaxonomyValidator
from models.question import EnrichmentRecord

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def load_taxonomy(filepath: str) -> dict:
    with open(filepath, 'r') as f:
        return json.load(f)

def run_enrichment(db: DatabaseManager, questions: list, llm_provider, taxonomy: dict, taxonomy_version: str, run_id: str, is_dry_run: bool = False):
    validator = TaxonomyValidator(taxonomy)
    llm_provider_name = os.getenv("LLM_PROVIDER", "gemini")
    llm_model_name = os.getenv("LLM_MODEL", "gemini-1.5-pro")
    llm_prompt_version = "v1.0"
    
    results = []
    
    for i, q in enumerate(questions):
        logger.info(f"Processing {i+1}/{len(questions)}: {q['golden_question_id']}")
        
        # Check cache
        if not is_dry_run:
            existing = db.get_enrichment(q['golden_question_id'])
            if existing and existing.get('validation_status') == 'VALID':
                if (existing.get('taxonomy_version') == taxonomy_version and 
                    existing.get('llm_provider') == llm_provider_name and
                    existing.get('llm_model') == llm_model_name and
                    existing.get('llm_prompt_version') == llm_prompt_version):
                    logger.info(f"Using cached enrichment for {q['golden_question_id']}")
                    results.append(existing)
                    continue
        
        # Prepare inputs
        options = q['options_json']
        if isinstance(options, str):
            options = json.loads(options) if options else {}
            
        try:
            # Call LLM
            llm_result = llm_provider.enrich_question(
                question_text=q['question_text'],
                options=options,
                marks=q['marks'] or 1.0,
                taxonomy=taxonomy
            )
            
            # Validate Taxonomy
            is_valid, err_msg = validator.validate(llm_result)
            validation_status = 'VALID' if is_valid else 'FAILED'
            
            # Create Record
            record = EnrichmentRecord(
                enrichment_id=str(uuid.uuid4()),
                golden_question_id=q['golden_question_id'],
                taxonomy_version=taxonomy_version,
                validation_status=validation_status,
                error_message=err_msg,
                ai_subject=llm_result.get('subject'),
                ai_topic=llm_result.get('topic'),
                ai_subtopic=llm_result.get('subtopic'),
                core_concepts=llm_result.get('concepts', []),
                difficulty_score=llm_result.get('difficulty', {}).get('score'),
                difficulty_confidence=llm_result.get('difficulty', {}).get('confidence'),
                difficulty_rationale=llm_result.get('difficulty', {}).get('rationale'),
                cognitive_level=llm_result.get('difficulty', {}).get('cognitive_level'),
                embedding_model=None, # Will be done in a separate embedding step
                embedding_version=None,
                embedding=None,
                llm_provider=llm_provider_name,
                llm_model=llm_model_name,
                llm_prompt_version=llm_prompt_version,
                enrichment_run_id=run_id,
                created_at=datetime.now()
            )
            
            if not is_dry_run:
                db.insert_enrichment(record)
                
            # Convert dataclass back to dict for immediate use
            record_dict = record.__dict__.copy()
            results.append(record_dict)
            
        except Exception as e:
            logger.error(f"Error enriching {q['golden_question_id']}: {e}")
            # Insert a failed record
            failed_record = EnrichmentRecord(
                enrichment_id=str(uuid.uuid4()),
                golden_question_id=q['golden_question_id'],
                taxonomy_version=taxonomy_version,
                validation_status='FAILED',
                error_message=str(e),
                ai_subject=None, ai_topic=None, ai_subtopic=None, core_concepts=[],
                difficulty_score=None, difficulty_confidence=None, difficulty_rationale=None,
                cognitive_level=None, embedding_model=None, embedding_version=None, embedding=None,
                llm_provider=llm_provider_name, llm_model=llm_model_name, llm_prompt_version=llm_prompt_version,
                enrichment_run_id=run_id, created_at=datetime.now()
            )
            if not is_dry_run:
                db.insert_enrichment(failed_record)
            results.append(failed_record.__dict__.copy())
            
    return results

def evaluate(results: list, gold_labels: dict):
    # gold_labels: dict of golden_question_id -> dict of gold fields
    metrics = {
        "total_evaluated": 0,
        "subject_correct": 0,
        "topic_correct": 0,
        "difficulty_errors": [],
        "confidence_bins": {
            "0.0-0.5": {"total": 0, "correct": 0},
            "0.5-0.8": {"total": 0, "correct": 0},
            "0.8-1.0": {"total": 0, "correct": 0}
        }
    }
    
    for r in results:
        qid = r['golden_question_id']
        if qid not in gold_labels:
            continue
            
        gold = gold_labels[qid]
        if not gold.get('gold_subject'):
            continue # Skip if human hasn't labeled it yet
            
        metrics["total_evaluated"] += 1
        
        # Subject Accuracy
        is_subj_correct = (r.get('ai_subject') == gold.get('gold_subject'))
        if is_subj_correct:
            metrics["subject_correct"] += 1
            
        # Topic Accuracy
        is_topic_correct = (r.get('ai_topic') == gold.get('gold_topic'))
        if is_topic_correct:
            metrics["topic_correct"] += 1
            
        # Difficulty MAE
        ai_diff = r.get('difficulty_score')
        human_diff = gold.get('human_difficulty')
        if ai_diff is not None and human_diff:
            try:
                metrics["difficulty_errors"].append(abs(float(ai_diff) - float(human_diff)))
            except ValueError:
                pass
                
        # Confidence Calibration
        conf = r.get('difficulty_confidence')
        if conf is not None:
            bin_key = "0.0-0.5" if conf <= 0.5 else "0.5-0.8" if conf <= 0.8 else "0.8-1.0"
            metrics["confidence_bins"][bin_key]["total"] += 1
            if is_subj_correct and is_topic_correct:
                metrics["confidence_bins"][bin_key]["correct"] += 1
                
    # Summarize
    if metrics["total_evaluated"] > 0:
        subj_acc = metrics["subject_correct"] / metrics["total_evaluated"]
        topic_acc = metrics["topic_correct"] / metrics["total_evaluated"]
        mae = sum(metrics["difficulty_errors"]) / len(metrics["difficulty_errors"]) if metrics["difficulty_errors"] else 0.0
        
        logger.info(f"--- Evaluation Metrics ({metrics['total_evaluated']} samples) ---")
        logger.info(f"Subject Accuracy: {subj_acc:.2%}")
        logger.info(f"Topic Accuracy: {topic_acc:.2%}")
        logger.info(f"Difficulty MAE: {mae:.2f}")
        
        for b, stats in metrics["confidence_bins"].items():
            if stats["total"] > 0:
                acc = stats["correct"] / stats["total"]
                logger.info(f"Confidence Bin {b}: {acc:.2%} accuracy (n={stats['total']})")
    else:
        logger.warning("No labeled data found in the provided gold set. Please fill in gold_subject, gold_topic, etc.")

def main():
    parser = argparse.ArgumentParser(description="Run AI Enrichment Pipeline.")
    parser.add_argument('--sample', type=int, help="Run a smoke test on N random questions.")
    parser.add_argument('--evaluate', type=str, help="Path to gold_set.csv to evaluate against.")
    parser.add_argument('--all', action='store_true', help="Run enrichment on all golden questions.")
    
    args = parser.parse_args()
    
    if not (args.sample or args.evaluate or args.all):
        logger.error("Must specify --sample N, --evaluate PATH, or --all")
        sys.exit(1)
        
    db = DatabaseManager(DB_PATH)
    taxonomy_path = "taxonomy/gate_cse_v1.json"
    taxonomy = load_taxonomy(taxonomy_path)
    taxonomy_version = "gate_cse_v1"
    
    provider_name = os.getenv("LLM_PROVIDER", "gemini")
    model_name = os.getenv("LLM_MODEL", "gemini-1.5-pro")
    llm = get_llm_provider(provider_name, model_name)
    
    run_id = f"enrich_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}"
    
    questions = []
    
    if args.evaluate:
        gold_labels = {}
        with open(args.evaluate, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                gold_labels[row['golden_question_id']] = row
                
        # Fetch these specific questions from DB
        all_q = []
        with db.get_connection() as conn:
            cursor = conn.cursor()
            for qid in gold_labels.keys():
                cursor.execute("SELECT * FROM golden_questions WHERE golden_question_id = ?", (qid,))
                row = cursor.fetchone()
                if row:
                    all_q.append(dict(row))
        questions = all_q
        logger.info(f"Loaded {len(questions)} questions for evaluation from {args.evaluate}")
        
    elif args.sample:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM golden_questions ORDER BY RANDOM() LIMIT ?", (args.sample,))
            questions = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Sampled {len(questions)} random questions.")
        
    elif args.all:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM golden_questions")
            questions = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Loaded {len(questions)} questions for full enrichment run.")
        
    # Run
    results = run_enrichment(db, questions, llm, taxonomy, taxonomy_version, run_id, is_dry_run=bool(args.sample))
    
    if args.evaluate:
        evaluate(results, gold_labels)
        
    logger.info("Enrichment pipeline complete.")

if __name__ == "__main__":
    main()
