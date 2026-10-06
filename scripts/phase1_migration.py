import sqlite3
import shutil
import os
import json
import hashlib
from datetime import datetime

DB_PATH = "data/db/gate_forecasting.db"
BACKUP_PATH = "data/db/gate_forecasting_backup.db"

def backup_db():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database {DB_PATH} not found.")
        return False
        
    print(f"Backing up database to {BACKUP_PATH}...")
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print("Backup successful.")
    return True

def run_migrations():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Running schema migrations...")
    
    # 1. VERSIONING & EXPERIMENTS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            experiment_id TEXT PRIMARY KEY,
            baseline_version TEXT,
            candidate_version TEXT,
            description TEXT,
            training_years TEXT,
            validation_years TEXT,
            metrics_json TEXT,
            decision TEXT,
            created_at TEXT
        )
    """)
    
    # Check if old model_versions exists with old schema
    try:
        cursor.execute("SELECT pipeline_version FROM model_versions LIMIT 1")
    except sqlite3.OperationalError:
        print("Dropping old model_versions table to update schema...")
        cursor.execute("DROP TABLE IF EXISTS model_versions")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_versions (
            version_id TEXT PRIMARY KEY,
            data_version TEXT,
            taxonomy_version TEXT,
            feature_version TEXT,
            model_type TEXT,
            hyperparameters_json TEXT,
            calibration_version TEXT,
            strategy_version TEXT,
            random_seed INTEGER,
            training_window TEXT,
            pipeline_version TEXT,
            code_hash TEXT,
            environment_hash TEXT,
            config_hash TEXT,
            is_baseline BOOLEAN,
            created_at TEXT
        )
    """)
    
    # 2. EVIDENCE & PATTERNS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidence_records (
            evidence_id TEXT PRIMARY KEY,
            prediction_id TEXT,
            historical_frequency INTEGER,
            recent_frequency INTEGER,
            current_gap INTEGER,
            average_gap REAL,
            trend TEXT,
            xgboost_score REAL,
            ema_score REAL,
            evidence_strength TEXT,
            confidence TEXT,
            supporting_questions_json TEXT,
            created_at TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS surprise_events (
            surprise_id TEXT PRIMARY KEY,
            exam_year INTEGER,
            concept TEXT,
            surprise_score REAL,
            surprise_category TEXT,
            reason TEXT,
            historical_trace_json TEXT,
            created_at TEXT
        )
    """)
    
    # 3. MOCK TESTS (Isolated Namespace)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mock_test_questions (
            mock_question_id TEXT PRIMARY KEY,
            mock_paper_id TEXT,
            subject TEXT,
            topic TEXT,
            concept TEXT,
            marks REAL,
            question_type TEXT,
            difficulty TEXT,
            question_text TEXT,
            options_json TEXT,
            answer TEXT,
            solution_explanation TEXT,
            plagiarism_check_status TEXT,
            created_at TEXT
        )
    """)
    
    conn.commit()
    print("Schema migrations applied successfully.")
    
    # Freeze Baseline V0
    print("Freezing Baseline V0...")
    
    # Calculate a hash of the current golden questions to prove data version
    cursor.execute("SELECT golden_question_id FROM golden_questions ORDER BY golden_question_id")
    all_ids = "".join([row[0] for row in cursor.fetchall()])
    db_hash = hashlib.sha256(all_ids.encode()).hexdigest()[:12]
    
    data_version = f"golden_v1.0_{db_hash}"
    v0_id = "xgb_ema_v0_baseline"
    
    # Check if V0 already exists
    cursor.execute("SELECT version_id FROM model_versions WHERE version_id = ?", (v0_id,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO model_versions (
                version_id, data_version, taxonomy_version, feature_version, 
                model_type, hyperparameters_json, calibration_version, strategy_version, random_seed, 
                training_window, pipeline_version, code_hash, environment_hash, config_hash, is_baseline, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            v0_id,
            data_version,
            "gate_cse_v1.0",
            "features_v0_basic",
            "XGBoost+EMA Ensemble",
            json.dumps({"xgb_weight": 0.6, "ema_weight": 0.4}),
            "calib_v0_none",
            "strat_v0_none",
            42,
            "1987-2025",
            "pipeline_v0.1_alpha",
            "code_hash_placeholder",
            "env_hash_placeholder",
            "cfg_hash_placeholder",
            True,
            datetime.now().isoformat()
        ))
        conn.commit()
        print(f"Baseline {v0_id} frozen successfully with Data Version {data_version}.")
    else:
        print(f"Baseline {v0_id} already exists. Skipping freeze.")
        
    conn.close()

if __name__ == "__main__":
    if backup_db():
        run_migrations()
