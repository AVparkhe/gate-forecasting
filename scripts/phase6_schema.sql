CREATE TABLE IF NOT EXISTS model_versions (
    model_version TEXT PRIMARY KEY,
    parent_version TEXT,
    model_type TEXT,
    feature_version TEXT,
    strategy_version TEXT,
    training_start_year INTEGER,
    training_end_year INTEGER,
    hyperparameters TEXT,
    status TEXT,
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS forecast_runs (
    run_id TEXT PRIMARY KEY,
    target_year INTEGER,
    training_start_year INTEGER,
    training_end_year INTEGER,
    model_version TEXT,
    feature_version TEXT,
    prediction_timestamp TIMESTAMP,
    status TEXT
);

CREATE TABLE IF NOT EXISTS prediction_matches (
    match_id TEXT PRIMARY KEY,
    run_id TEXT,
    predicted_id TEXT,
    actual_question_id TEXT,
    subject_match TEXT,
    topic_match TEXT,
    subtopic_match TEXT,
    concept_match TEXT,
    marks_match TEXT,
    question_type_match TEXT,
    difficulty_match TEXT,
    match_score REAL,
    match_status TEXT,
    failure_category TEXT,
    explanation TEXT
);

CREATE TABLE IF NOT EXISTS iteration_evaluations (
    run_id TEXT PRIMARY KEY,
    actual_year INTEGER,
    precision REAL,
    recall REAL,
    f1 REAL,
    precision_at_k REAL,
    recall_at_k REAL,
    ndcg REAL,
    marks_mae REAL,
    brier_score REAL
);

CREATE TABLE IF NOT EXISTS learning_ledger (
    id TEXT PRIMARY KEY,
    iteration_id TEXT,
    target_year INTEGER,
    model_version TEXT,
    strategy_version TEXT,
    parent_strategy_version TEXT,
    failure_category TEXT,
    failure_description TEXT,
    hypothesis TEXT,
    strategy_update_proposed TEXT,
    before_f1 REAL,
    after_f1 REAL,
    backtest_years TEXT,
    status TEXT,
    acceptance_reason TEXT,
    rejection_reason TEXT
);

CREATE TABLE IF NOT EXISTS forecast_predictions (
    run_id TEXT,
    prediction_id TEXT PRIMARY KEY,
    subject TEXT,
    topic TEXT,
    subtopic TEXT,
    concept TEXT,
    marks REAL,
    question_type TEXT,
    difficulty TEXT,
    probability REAL,
    rank INTEGER,
    confidence TEXT,
    prediction_level TEXT,
    prediction_source TEXT,
    evidence_id TEXT
);
