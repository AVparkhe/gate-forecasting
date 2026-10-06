import sys
import json
import sqlite3
import random
import uuid
from pathlib import Path
from datetime import datetime

# Adjust path to import local modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DB_PATH

def run_mock_enrichment():
    db_path = DB_PATH
    taxonomy_path = "taxonomy/gate_cse_v1.json"
    
    with open(taxonomy_path, 'r') as f:
        taxonomy = json.load(f)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT golden_question_id FROM golden_questions")
    questions = cursor.fetchall()
    
    subjects = list(taxonomy.keys())
    
    count = 0
    run_id = f"mock_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    for q in questions:
        qid = q[0]
        
        # Pick random taxonomy path
        subject = random.choice(subjects)
        topics = list(taxonomy[subject].keys())
        topic = random.choice(topics) if topics else None
        
        subtopics = taxonomy[subject][topic] if topic else []
        subtopic_name = random.choice(subtopics) if subtopics else None
        
        concept_name = subtopic_name
        
        # Format concepts for DB (list of dicts as JSON string)
        core_concepts = json.dumps([{"name": concept_name, "weight": 1.0}]) if concept_name else "[]"
        
        enrichment_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO question_enrichment (
                enrichment_id, golden_question_id, taxonomy_version, validation_status,
                ai_subject, ai_topic, ai_subtopic, core_concepts,
                difficulty_score, difficulty_confidence, cognitive_level,
                llm_provider, llm_model, enrichment_run_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            enrichment_id, qid, "gate_cse_v1", "VALID",
            subject, topic, subtopic_name, core_concepts,
            random.uniform(1.0, 5.0), random.uniform(0.6, 0.99), "APPLY",
            "MOCK", "MOCK-1.0", run_id, datetime.now().isoformat()
        ))
        
        count += 1
        
    conn.commit()
    conn.close()
    print(f"Successfully populated {count} mock enrichment records!")

if __name__ == "__main__":
    run_mock_enrichment()
