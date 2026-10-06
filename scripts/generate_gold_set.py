import sqlite3
import csv
import random
import logging
from pathlib import Path
import sys

# Adjust path to import local modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DB_PATH

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def generate_gold_set(db_path: Path, output_csv: Path, sample_size: int = 250):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # We want a stratified sample based on:
    # 1. Year (Old vs New)
    # 2. Subject (Based on go_subject)
    # 3. Question Type (MCQ vs NAT vs MSQ)
    # We can group by year bins and subjects to ensure variety.
    
    cursor.execute("""
        SELECT golden_question_id, exam_year, paper, session, question_number, 
               question_text, options_json, go_subject, go_topic, question_type, marks
        FROM golden_questions
    """)
    all_questions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if not all_questions:
        logger.error("No questions found in golden_questions table.")
        return

    # Bucket questions to ensure stratification
    buckets = {}
    for q in all_questions:
        # Year bucket: old (<2010), mid (2010-2018), new (>2018)
        y = q['exam_year']
        if y < 2010:
            y_bucket = "old"
        elif y <= 2018:
            y_bucket = "mid"
        else:
            y_bucket = "new"
            
        subj = q['go_subject'] if q['go_subject'] else "UNKNOWN"
        qtype = q['question_type'] if q['question_type'] else "UNKNOWN"
        
        # We group by (subject, year_bucket) to get diverse coverage
        key = (subj, y_bucket)
        if key not in buckets:
            buckets[key] = []
        buckets[key].append(q)
        
    # Sample proportionally from each bucket
    sampled = []
    total_buckets = len(buckets)
    if total_buckets == 0:
        return
        
    # Try to pick a roughly equal number from each bucket to reach sample_size
    target_per_bucket = max(1, sample_size // total_buckets)
    
    # Simple proportional allocation
    for key, items in buckets.items():
        sample_count = min(target_per_bucket, len(items))
        sampled.extend(random.sample(items, sample_count))
        
    # If we fall short, pad with random questions not yet sampled
    if len(sampled) < sample_size:
        sampled_ids = {s['golden_question_id'] for s in sampled}
        remaining = [q for q in all_questions if q['golden_question_id'] not in sampled_ids]
        shortfall = min(sample_size - len(sampled), len(remaining))
        sampled.extend(random.sample(remaining, shortfall))
        
    # Cap at sample_size in case buckets exceeded it
    if len(sampled) > sample_size:
        random.shuffle(sampled)
        sampled = sampled[:sample_size]
        
    # Prepare CSV data
    # Include the columns the human reviewer will fill out
    fieldnames = [
        "golden_question_id", "exam_year", "paper", "session", "question_number",
        "question_text", "options_json", "marks", "question_type", 
        "go_subject", "go_topic",
        "taxonomy_version", "gold_subject", "gold_topic", "gold_subtopic",
        "human_difficulty", "gold_cognitive_level", "gold_concepts", "reviewer_notes"
    ]
    
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for q in sampled:
            row = {
                "golden_question_id": q["golden_question_id"],
                "exam_year": q["exam_year"],
                "paper": q["paper"],
                "session": q["session"],
                "question_number": q["question_number"],
                "question_text": q["question_text"],
                "options_json": q["options_json"],
                "marks": q["marks"],
                "question_type": q["question_type"],
                "go_subject": q["go_subject"],
                "go_topic": q["go_topic"],
                "taxonomy_version": "gate_cse_v1", # from our spec
                "gold_subject": "",
                "gold_topic": "",
                "gold_subtopic": "",
                "human_difficulty": "",
                "gold_cognitive_level": "",
                "gold_concepts": "",
                "reviewer_notes": ""
            }
            writer.writerow(row)
            
    logger.info(f"Successfully generated a stratified Gold Set of {len(sampled)} questions at {output_csv}")

if __name__ == "__main__":
    out_path = Path("data/review/gold_set.csv")
    generate_gold_set(DB_PATH, out_path, sample_size=250)
