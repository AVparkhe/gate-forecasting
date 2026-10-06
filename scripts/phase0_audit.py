import sqlite3
import json
import os

DB_PATH = "data/db/gate_forecasting.db"
OUTPUT_PATH = "data_quality_report.json"

def run_audit():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            gq.golden_question_id,
            gq.exam_year,
            gq.marks,
            gq.question_type,
            gq.official_id,
            gq.go_id,
            qe.ai_subject,
            qe.ai_topic,
            qe.core_concepts,
            qe.difficulty_score
        FROM golden_questions gq
        LEFT JOIN question_enrichment qe ON gq.golden_question_id = qe.golden_question_id
    """)
    rows = cursor.fetchall()

    total_records = len(rows)
    if total_records == 0:
        print("No records found.")
        return
        
    official_count = 0
    go_count = 0
    both_count = 0
    official_only = 0
    go_only = 0
    
    for row in rows:
        has_off = bool(row['official_id'])
        has_go = bool(row['go_id'])
        if has_off: official_count += 1
        if has_go: go_count += 1
        if has_off and has_go: both_count += 1
        if has_off and not has_go: official_only += 1
        if not has_off and has_go: go_only += 1

    coverage = {
        "year": 0,
        "subject": 0,
        "topic": 0,
        "concept": 0,
        "marks": 0,
        "difficulty": 0,
        "type": 0
    }
    
    record_status_counts = {
        "VERIFIED": 0,
        "PARTIAL": 0,
        "INVALID": 0
    }
    
    year_coverage = {}

    for row in rows:
        year = row['exam_year']
        if year not in year_coverage:
            year_coverage[year] = {"total": 0, "verified": 0, "partial": 0, "invalid": 0}
        
        year_coverage[year]["total"] += 1

        fields_present = 0
        total_fields = 7
        
        has_year = year is not None
        has_subject = bool(row['ai_subject'])
        has_topic = bool(row['ai_topic'])
        has_concept = bool(row['core_concepts']) and row['core_concepts'] != '[]'
        has_marks = row['marks'] is not None
        has_difficulty = row['difficulty_score'] is not None
        has_type = bool(row['question_type'])

        if has_year: coverage["year"] += 1
        if has_subject: coverage["subject"] += 1
        if has_topic: coverage["topic"] += 1
        if has_concept: coverage["concept"] += 1
        if has_marks: coverage["marks"] += 1
        if has_difficulty: coverage["difficulty"] += 1
        if has_type: coverage["type"] += 1

        score = (has_year + has_subject + has_topic + has_concept + has_marks + has_difficulty + has_type) / total_fields

        if score == 1.0:
            status = "VERIFIED"
        elif score >= 0.5:
            status = "PARTIAL"
        else:
            status = "INVALID"
            
        record_status_counts[status] += 1
        year_coverage[year][status.lower()] += 1

    # Check 2026 completion
    is_2026_complete = False
    if 2026 in year_coverage:
        stats_2026 = year_coverage[2026]
        # Assuming a typical CSE paper has ~65 questions
        if stats_2026["total"] >= 65 and (stats_2026["verified"] / stats_2026["total"]) > 0.90:
            is_2026_complete = True

    report = {
        "dataset_composition": {
            "total_records": total_records,
            "statement": f"{total_records} is the complete canonical Golden Dataset.",
            "sources": {
                "official_questions": official_count,
                "gate_overflow_questions": go_count,
                "both_sources": both_count,
                "official_only": official_only,
                "go_only": go_only
            }
        },
        "record_status": {
            "VERIFIED": record_status_counts["VERIFIED"],
            "PARTIAL": record_status_counts["PARTIAL"],
            "INVALID": record_status_counts["INVALID"]
        },
        "coverage_percentages": {k: round((v / total_records) * 100, 2) for k, v in coverage.items()},
        "is_2026_verified": is_2026_complete,
        "latest_verified_year": max([y for y, s in year_coverage.items() if s["total"] >= 65 and (s["verified"]/s["total"]) > 0.5], default=None)
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(report, f, indent=4)
        
    print(f"Data audit complete. Report saved to {OUTPUT_PATH}")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    run_audit()
