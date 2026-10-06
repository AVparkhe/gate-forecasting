import sqlite3
import json
import os
import pandas as pd
import numpy as np

DB_PATH = "data/db/gate_forecasting.db"

def init_feature_store(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feature_store (
            target_year INTEGER,
            subject TEXT,
            topic TEXT,
            concept TEXT,
            historical_frequency INTEGER,
            recent_frequency INTEGER,
            current_gap INTEGER,
            average_gap REAL,
            max_gap INTEGER,
            lifecycle_status TEXT,
            feature_version TEXT,
            PRIMARY KEY (target_year, concept)
        )
    """)
    conn.commit()

def calculate_lifecycle(hist_freq, recent_freq_3, gap, max_gap):
    if hist_freq == 0:
        return "NEW_OR_UNTESTED"
    
    if gap >= 15:
        return "VANISHED"
    if gap >= 10:
        return "LONG-DORMANT"
    if gap >= 5:
        return "DORMANT"
        
    if hist_freq < 5 and recent_freq_3 >= 2:
        return "EMERGING"
        
    if gap <= 3 and hist_freq >= 5:
        return "ACTIVE"
        
    return "RECURRING"

def compute_features_for_year(conn, target_year):
    # Leakage Prevention: STRICTLY filter out target_year and beyond
    query = """
        SELECT 
            qe.ai_subject as subject,
            qe.ai_topic as topic,
            qe.core_concepts as concept_json,
            gq.exam_year
        FROM golden_questions gq
        JOIN question_enrichment qe ON gq.golden_question_id = qe.golden_question_id
        WHERE gq.exam_year < ?
    """
    
    df = pd.read_sql_query(query, conn, params=(target_year,))
    
    # Flatten concepts
    flattened = []
    for _, row in df.iterrows():
        try:
            concepts_data = json.loads(row['concept_json'])
            if isinstance(concepts_data, list):
                concepts = []
                for c in concepts_data:
                    if isinstance(c, dict) and 'name' in c:
                        concepts.append(c['name'])
                    elif isinstance(c, str):
                        concepts.append(c)
            elif isinstance(concepts_data, dict) and 'name' in concepts_data:
                concepts = [concepts_data['name']]
            else:
                concepts = [str(concepts_data)]
        except:
            concepts = [str(row['concept_json'])] if row['concept_json'] else []
            
        for c in concepts:
            if not c or c == '[]' or c == 'None': continue
            flattened.append({
                'exam_year': row['exam_year'],
                'subject': row['subject'],
                'topic': row['topic'],
                'concept': c
            })
            
    if not flattened:
        return []
        
    flat_df = pd.DataFrame(flattened)
    
    features = []
    grouped = flat_df.groupby(['subject', 'topic', 'concept'])
    
    for (subj, topic, concept), group in grouped:
        years_appeared = sorted(group['exam_year'].unique())
        if not years_appeared: continue
        
        # Hard Feature Leakage Test: Ensure no source year is >= target_year
        if max(years_appeared) >= target_year:
            raise AssertionError(f"CRITICAL FEATURE LEAKAGE: Concept '{concept}' for target_year {target_year} used source data from {max(years_appeared)}!")
        
        hist_freq = len(years_appeared)
        recent_freq_5 = len([y for y in years_appeared if target_year - y <= 5])
        recent_freq_3 = len([y for y in years_appeared if target_year - y <= 3])
        
        last_appearance = years_appeared[-1]
        current_gap = target_year - last_appearance
        
        gaps = [years_appeared[i] - years_appeared[i-1] for i in range(1, len(years_appeared))]
        avg_gap = np.mean(gaps) if gaps else 0
        max_gap = max(gaps) if gaps else 0
        
        lifecycle = calculate_lifecycle(hist_freq, recent_freq_3, current_gap, max_gap)
        
        features.append((
            int(target_year), str(subj), str(topic), str(concept),
            int(hist_freq), int(recent_freq_5), int(current_gap), float(avg_gap), int(max_gap),
            str(lifecycle), 'features_v2_advanced'
        ))
        
    return features

def run_feature_pipeline():
    conn = sqlite3.connect(DB_PATH)
    init_feature_store(conn)
    cursor = conn.cursor()
    
    # Clear old
    cursor.execute("DELETE FROM feature_store WHERE feature_version = 'features_v2_advanced'")
    
    # Compute for every target year from 2000 to 2027
    print("Computing advanced features (with strict temporal isolation)...")
    for year in range(2000, 2028):
        features = compute_features_for_year(conn, year)
        if features:
            cursor.executemany("""
                INSERT OR REPLACE INTO feature_store 
                (target_year, subject, topic, concept, historical_frequency, recent_frequency, 
                 current_gap, average_gap, max_gap, lifecycle_status, feature_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, features)
            
    conn.commit()
    
    # TEMPORAL LEAKAGE TEST
    # Verify that for target_year 2025, no concept has a current_gap of 0 (which would mean it was tested IN 2025)
    # The minimum gap should be 1 (last tested in 2024).
    cursor.execute("SELECT MIN(current_gap) FROM feature_store WHERE target_year = 2025")
    min_gap = cursor.fetchone()[0]
    
    if min_gap is not None and isinstance(min_gap, bytes):
        min_gap = int.from_bytes(min_gap, byteorder='little')
        
    if min_gap is None or int(min_gap) < 1:
        print(f"CRITICAL ERROR: Temporal Leakage detected! Minimum gap is {min_gap}.")
    else:
        print(f"SUCCESS: Feature Leakage Test Passed. Minimum gap for target_year is correctly >= 1 (Actual: {min_gap}).")
        
    conn.close()
    print("Phase 2 feature extraction complete.")

if __name__ == "__main__":
    run_feature_pipeline()
