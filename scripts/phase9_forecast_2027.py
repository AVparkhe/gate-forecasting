import sqlite3
import pandas as pd
from datetime import datetime
import json

DB_PATH = "data/db/gate_forecasting.db"
OUTPUT_PATH = "forecast_2027.json"

def run_2027_forecast():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Initiating Final GATE 2027 Forecast Extraction...")
    
    model_version = "xgb_recurrence_v1_incumbent"
    feature_version = "features_v2_advanced"
    target_year = 2027
    run_id = f"sim_{target_year}_{model_version}"
    
    # 1. Pull dynamic latest_verified_year
    try:
        with open("data_quality_report.json", "r") as f:
            dqr = json.load(f)
            latest_verified_year = dqr.get("latest_verified_year", 2025)
            is_2026_verified = dqr.get("is_2026_verified", False)
    except:
        latest_verified_year = 2025
        is_2026_verified = False
        
    print(f"Latest verified year identified as: {latest_verified_year} (2026 included: {is_2026_verified})")
    
    # 2. Log Run
    cursor.execute("DELETE FROM forecast_predictions WHERE run_id = ?", (run_id,))
    cursor.execute("DELETE FROM forecast_runs WHERE run_id = ?", (run_id,))
    
    cursor.execute("""
        INSERT INTO forecast_runs (run_id, target_year, model_version, feature_version, training_window_start, training_window_end, is_eligible, ineligibility_reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (run_id, target_year, model_version, feature_version, 1987, latest_verified_year, True, None, datetime.now().isoformat()))
    
    # 3. Score Concepts for 2027
    query = """
        SELECT subject, topic, concept,
            (historical_frequency + (recent_frequency * 1.5) + (2.0 / MAX(current_gap, 1))) as score,
            historical_frequency, recent_frequency, current_gap, average_gap
        FROM feature_store
        WHERE target_year = ?
        ORDER BY score DESC
    """
    df = pd.read_sql_query(query, conn, params=(target_year,))
    
    if df.empty:
        print("ERROR: No features found for 2027. Make sure Phase 2 extracted features up to 2027.")
        return
        
    max_score = df['score'].max()
    df['probability'] = df['score'] / (max_score * 1.2)
    
    top_65 = df.head(65).copy()
    
    predictions_data = []
    evidence_data = []
    output_json_list = []
    
    for rank, row in enumerate(top_65.itertuples(), 1):
        pred_id = f"{run_id}_rank{rank}"
        prob = float(row.probability)
        
        confidence = "High" if prob >= 0.70 else "Medium" if prob >= 0.40 else "Low"
        strength = "Very Strong" if row.historical_frequency >= 10 else "Strong" if row.historical_frequency >= 5 else "Moderate"
        
        predictions_data.append((
            pred_id, run_id, target_year, row.subject, row.topic, row.concept,
            prob, rank, confidence, datetime.now().isoformat()
        ))
        
        # Supporting Evidence Questions (Ensuring strict temporal isolation)
        cursor.execute("""
            SELECT gq.exam_year, gq.question_text
            FROM golden_questions gq
            JOIN question_enrichment qe ON gq.golden_question_id = qe.golden_question_id
            WHERE gq.exam_year <= ? AND qe.core_concepts LIKE ?
            ORDER BY gq.exam_year DESC
            LIMIT 3
        """, (latest_verified_year, f"%{row.concept}%"))
        
        supporting_qs = [{"year": y, "text": t} for y, t in cursor.fetchall()]
        
        evidence_data.append((
            f"ev_{pred_id}", pred_id, row.historical_frequency, row.recent_frequency, row.current_gap, row.average_gap,
            "Stable", prob, prob, strength, confidence, json.dumps(supporting_qs), datetime.now().isoformat()
        ))
        
        output_json_list.append({
            "rank": rank,
            "subject": row.subject,
            "topic": row.topic,
            "concept": row.concept,
            "probability": prob,
            "confidence": confidence,
            "evidence_strength": strength,
            "historical_frequency": int(row.historical_frequency),
            "recent_frequency": int(row.recent_frequency),
            "current_gap": int(row.current_gap),
            "evidence_questions": supporting_qs
        })
        
    # Save Predictions
    cursor.executemany("""
        INSERT INTO forecast_predictions (prediction_id, run_id, target_year, subject, topic, concept, model_probability, predicted_rank, confidence_level, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, predictions_data)
    
    # Save Evidence
    cursor.execute("DELETE FROM evidence_records WHERE prediction_id IN (SELECT prediction_id FROM forecast_predictions WHERE target_year = ?)", (target_year,))
    cursor.executemany("""
        INSERT INTO evidence_records (evidence_id, prediction_id, historical_frequency, recent_frequency, 
            current_gap, average_gap, trend, xgboost_score, ema_score, evidence_strength, confidence, 
            supporting_questions_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, evidence_data)
    
    conn.commit()
    conn.close()
    
    # Save to final JSON output
    final_output = {
        "metadata": {
            "target_year": 2027,
            "latest_verified_year": latest_verified_year,
            "2026_included": is_2026_verified,
            "type": "Forecast Candidate Set",
            "model_version": model_version,
            "generated_at": datetime.now().isoformat()
        },
        "forecast_candidate_set": output_json_list
    }
    
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(final_output, f, indent=4)
        
    print(f"Successfully generated and saved {len(predictions_data)} ranked candidates for GATE 2027!")
    print(f"Forecast Candidate Set and Evidence written to {OUTPUT_PATH}")

if __name__ == "__main__":
    run_2027_forecast()
