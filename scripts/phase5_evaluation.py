import sqlite3
import pandas as pd
import json
from datetime import datetime

DB_PATH = "data/db/gate_forecasting.db"

def init_eval_tables(conn):
    cursor = conn.cursor()
    
    # Check and rename legacy tables
    try:
        cursor.execute("SELECT error_taxonomy FROM prediction_matches LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prediction_matches'")
        if cursor.fetchone():
            cursor.execute("ALTER TABLE prediction_matches RENAME TO legacy_prediction_matches")

    cursor.execute("DROP TABLE IF EXISTS prediction_matches")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_matches (
            match_id TEXT PRIMARY KEY,
            prediction_id TEXT,
            run_id TEXT,
            target_year INTEGER,
            concept TEXT,
            prediction_level TEXT,
            is_match BOOLEAN,
            error_taxonomy TEXT,
            trigger_feature TEXT,
            feature_value REAL,
            counterfactual_value REAL,
            created_at TEXT
        )
    """)
    conn.commit()

def get_actual_concepts(conn, target_year):
    query = """
        SELECT DISTINCT qe.core_concepts
        FROM golden_questions gq
        JOIN question_enrichment qe ON gq.golden_question_id = qe.golden_question_id
        WHERE gq.exam_year = ?
    """
    df = pd.read_sql_query(query, conn, params=(target_year,))
    actuals = []
    for _, row in df.iterrows():
        try:
            concepts = json.loads(row['core_concepts'])
            if isinstance(concepts, list):
                for c in concepts:
                    if isinstance(c, dict): actuals.append(c.get('name'))
                    elif isinstance(c, str): actuals.append(c)
            elif isinstance(concepts, dict): actuals.append(concepts.get('name'))
            else: actuals.append(str(concepts))
        except:
            actuals.append(str(row['core_concepts']))
    return set([c for c in actuals if c and c != '[]' and c != 'None'])

def determine_error_taxonomy(conn, concept, target_year, probability):
    if probability >= 0.75:
        return ("HIGH_CONFIDENCE_WRONG", "model_probability", probability, 0.40)
        
    cursor = conn.cursor()
    cursor.execute("""
        SELECT recent_frequency, current_gap 
        FROM feature_store 
        WHERE concept = ? AND target_year = ?
    """, (concept, target_year))
    row = cursor.fetchone()
    
    if row:
        recent_freq, current_gap = row
        if recent_freq >= 2:
            return ("RECENCY_MISJUDGMENT", "recent_frequency", recent_freq, 0.0)
        if current_gap <= 3:
            return ("RECURRENCE_MISJUDGMENT", "current_gap", current_gap, 5.0)
            
    return ("CONCEPT_MISS", None, None, None)

def run_evaluation():
    conn = sqlite3.connect(DB_PATH)
    init_eval_tables(conn)
    cursor = conn.cursor()
    
    print("Starting Prediction vs Actual Evaluation...")
    print("Note: All logic is structurally operating at prediction_level = CONCEPT.")
    
    # Process only runs that are eligible
    cursor.execute("SELECT run_id, target_year FROM forecast_runs WHERE is_eligible = True")
    runs = cursor.fetchall()
    
    cursor.execute("DELETE FROM prediction_matches")
    
    matches_data = []
    
    for run_id, target_year in runs:
        actuals = get_actual_concepts(conn, target_year)
        
        cursor.execute("""
            SELECT prediction_id, concept, model_probability
            FROM forecast_predictions
            WHERE run_id = ?
        """, (run_id,))
        predictions = cursor.fetchall()
        
        for pred_id, concept, prob in predictions:
            is_match = concept in actuals
            
            error_taxonomy = None
            trigger_feature = None
            feature_value = None
            counterfactual_value = None
            
            if not is_match:
                error_taxonomy, trigger_feature, feature_value, counterfactual_value = determine_error_taxonomy(conn, concept, target_year, prob)
                
            matches_data.append((
                f"match_{pred_id}", pred_id, run_id, target_year, concept,
                "CONCEPT", is_match, error_taxonomy, trigger_feature, feature_value, counterfactual_value, datetime.now().isoformat()
            ))
            
    if matches_data:
        cursor.executemany("""
            INSERT INTO prediction_matches (
                match_id, prediction_id, run_id, target_year, concept, 
                prediction_level, is_match, error_taxonomy, 
                trigger_feature, feature_value, counterfactual_value, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, matches_data)
        
    conn.commit()
    conn.close()
    
    print(f"Evaluated {len(runs)} simulated runs.")
    print(f"Inserted {len(matches_data)} match records with error taxonomies.")

if __name__ == "__main__":
    run_evaluation()
