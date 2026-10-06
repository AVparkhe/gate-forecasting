import sqlite3
import pandas as pd
import json
from datetime import datetime

DB_PATH = "data/db/gate_forecasting.db"

def init_surprise_tables(conn):
    # Table surprise_events was already created in Phase 1 migration
    pass

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

def run_surprise_detection():
    conn = sqlite3.connect(DB_PATH)
    init_surprise_tables(conn)
    cursor = conn.cursor()
    
    print("Starting Surprise Event Detection...")
    
    cursor.execute("DELETE FROM surprise_events")
    
    # Process only runs that are eligible
    cursor.execute("SELECT run_id, target_year FROM forecast_runs WHERE is_eligible = True")
    runs = cursor.fetchall()
    
    surprise_data = []
    
    for run_id, target_year in runs:
        actuals = get_actual_concepts(conn, target_year)
        
        cursor.execute("""
            SELECT concept, model_probability, predicted_rank
            FROM forecast_predictions
            WHERE run_id = ?
        """, (run_id,))
        
        predicted_rows = cursor.fetchall()
        predicted_concepts = {row[0]: row[1] for row in predicted_rows}
        
        # 1. Expected Absences (High Confidence Misses)
        for concept, prob in predicted_concepts.items():
            if prob >= 0.75 and concept not in actuals:
                warning = f"Hint: '{concept}' missed in {target_year} despite perfect recurrence setup. Do not assume it will appear just because it is 'due'."
                surprise_data.append((
                    f"surp_{run_id}_miss_{concept.replace(' ', '')}", target_year, concept,
                    1.0, "EXPECTED_ABSENCE", warning, "[]", datetime.now().isoformat()
                ))
                
        # 2. Unpredicted Outliers (Concepts that appeared but weren't predicted)
        for concept in actuals:
            if concept not in predicted_concepts:
                warning = f"Historical warning: This concept has previously appeared completely unpredicted in {target_year}. Treat it as a high-risk surprise concept."
                surprise_data.append((
                    f"surp_{run_id}_outlier_{concept.replace(' ', '')}", target_year, concept,
                    1.0, "UNPREDICTED_OUTLIER", warning, "[]", datetime.now().isoformat()
                ))
                
    if surprise_data:
        cursor.executemany("""
            INSERT OR REPLACE INTO surprise_events (surprise_id, exam_year, concept, surprise_score, surprise_category, reason, historical_trace_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, surprise_data)
        
    conn.commit()
    conn.close()
    
    print(f"Detected {len(surprise_data)} Surprise Events across all historical runs.")
    print("Surprise warnings and hints generated successfully.")

if __name__ == "__main__":
    run_surprise_detection()
