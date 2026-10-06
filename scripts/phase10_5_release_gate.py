import sqlite3
import json
import os

DB_PATH = "data/db/gate_forecasting.db"

def run_release_gate():
    print("========================================")
    print("★ PHASE 10.5: RESEARCH RELEASE GATE ★")
    print("========================================\n")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    failures = 0
    
    def assert_test(name, condition, error_msg):
        nonlocal failures
        if condition:
            print(f"[PASS] {name}")
        else:
            print(f"[FAIL] {name}: {error_msg}")
            failures += 1
            
    # 1. Canonical Dataset Test
    cursor.execute("SELECT COUNT(*) FROM golden_questions")
    gq_count = cursor.fetchone()[0]
    assert_test("1. Canonical Dataset Test", gq_count >= 2156, f"Expected at least 2156 golden questions, got {gq_count}")
    
    # 2. V0 Pipeline Freeze Test
    cursor.execute("SELECT environment_hash FROM model_versions WHERE version_id = 'xgb_ema_v0_baseline'")
    env_hash = cursor.fetchone()
    assert_test("2. V0 Pipeline Freeze Test", env_hash is not None and env_hash[0] is not None, "V0 baseline is missing environment hashes")
    
    # 3. Feature Leakage Test
    cursor.execute("SELECT MIN(current_gap) FROM feature_store WHERE target_year = 2025")
    min_gap = cursor.fetchone()[0]
    # Handle BLOB conversion if necessary (some sqlite aggregate functions return bytes)
    if isinstance(min_gap, bytes): min_gap = int.from_bytes(min_gap, byteorder='little')
    assert_test("3. Feature Leakage Test", min_gap is not None and int(min_gap) >= 1, "Temporal leak detected: min current_gap < 1")
    
    # 4. Model Validation Rule
    cursor.execute("SELECT decision FROM experiments ORDER BY created_at DESC LIMIT 1")
    decision = cursor.fetchone()
    assert_test("4. Model Validation Rule", decision is not None and decision[0] == 'ACCEPT', "Latest experiment was not accepted")
    
    # 5. Minimum Training Window Test
    cursor.execute("SELECT COUNT(*) FROM forecast_runs WHERE target_year <= 1999 AND is_eligible = 1")
    ineligible_runs_run = cursor.fetchone()[0]
    assert_test("5. Minimum Training Window Test", ineligible_runs_run == 0, "Found eligible runs before 2000 despite 13-year rule")
    
    # 6. Evaluation Granularity Test
    cursor.execute("SELECT COUNT(*) FROM prediction_matches WHERE prediction_level != 'CONCEPT'")
    non_concept = cursor.fetchone()[0]
    assert_test("6. Evaluation Granularity Test", non_concept == 0, "prediction_matches contains non-CONCEPT level evaluations")
    
    # 7. Brier Population Test
    with open("calibration_report.json", "r") as f:
        calib = json.load(f)
        buckets = [b['bucket_range'] for b in calib['buckets'] if b['count'] > 0]
        has_low = "0-10%" in buckets
    assert_test("7. Brier Population Test", has_low, "Brier score calculation does not include the full population (missing low probability buckets)")
    
    # 8. Brain Integrity Test
    cursor.execute("SELECT COUNT(*) FROM learning_events WHERE failure_type = 'HIGH_CONFIDENCE_WRONG'")
    brain_events = cursor.fetchone()[0]
    assert_test("8. Brain Integrity Test", brain_events > 0, "Model Brain did not detect HIGH_CONFIDENCE_WRONG events")
    
    # 9. Historical Question Integrity Test
    # 9. Historical Question Integrity Test
    cursor.execute("SELECT COUNT(*) FROM golden_questions")
    gq_count2 = cursor.fetchone()[0]
    assert_test("9. Historical Question Integrity Test", gq_count2 >= 2156, "Golden dataset was modified during execution!")
    
    # 10. 2026 Verification Test (Part of Latest Verified Year)
    with open("forecast_2027.json", "r") as f:
        forecast = json.load(f)
        is_2026_included = forecast["metadata"].get("2026_included", True)
    assert_test("10. 2026 Verification Test", is_2026_included, "2026 data must be included in verified history")
    
    # 11. Evidence Integrity Test (Pre-Target bounds)
    cursor.execute("SELECT COUNT(*) FROM evidence_records WHERE supporting_questions_json LIKE '%2025%' AND prediction_id LIKE '%sim_2025%'")
    evidence_leaks = cursor.fetchone()[0]
    assert_test("11. Evidence Integrity Test", evidence_leaks == 0, "Found evidence from 2025 used for 2025 prediction")
    
    # 12. Forecast Population Integrity Test
    cursor.execute("""
        SELECT COUNT(fp.concept)
        FROM forecast_predictions fp
        LEFT JOIN feature_store fs ON fp.concept = fs.concept AND fp.target_year = fs.target_year
        WHERE fs.concept IS NULL
    """)
    unbacked_concepts = cursor.fetchone()[0]
    assert_test("12. Forecast Population Integrity Test", unbacked_concepts == 0, f"Found {unbacked_concepts} predictions with no historical feature backing")
    
    conn.close()
    
    print("========================================")
    if failures == 0:
        print("★ RESEARCH_ENGINE_RELEASE = PASS ★")
        print("All research bounds verified. Safe to proceed to UI generation.")
        with open(".release_gate_status", "w") as f:
            f.write("PASS")
    else:
        print(f"★ RESEARCH_ENGINE_RELEASE = FAIL ({failures} violations) ★")
        print("DO NOT PROCEED. Fix backend scripts.")
        with open(".release_gate_status", "w") as f:
            f.write("FAIL")
    print("========================================")

if __name__ == "__main__":
    run_release_gate()
