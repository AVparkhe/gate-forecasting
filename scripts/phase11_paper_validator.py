import json
import os
from datetime import datetime

INPUT_PATH = "forecast_2027.json"
OUTPUT_PATH = "forecast_2027_paper_spec.json"

def run_paper_validator():
    print("==================================================")
    print("★ PHASE 11: 65-QUESTION FORECAST SPEC VALIDATOR ★")
    print("==================================================\n")
    
    if not os.path.exists(INPUT_PATH):
        print(f"ERROR: {INPUT_PATH} not found.")
        return
        
    with open(INPUT_PATH, "r") as f:
        forecast_data = json.load(f)
        
    candidates = forecast_data.get("forecast_candidate_set", [])
    
    if len(candidates) < 65:
        print(f"ERROR: Not enough candidates to form a 65-question paper. Found only {len(candidates)}.")
        return
        
    # Take top 65 candidates
    top_65 = candidates[:65]
    
    # Assign marks: Standard GATE pattern is 30 1-mark questions and 35 2-mark questions = 100 marks.
    # In a real system, we'd predict the mark distribution, but for the spec, we force this constraint.
    # Let's say top 35 are 2-marks (harder/core concepts), next 30 are 1-mark.
    paper_spec = []
    total_marks = 0
    total_questions = 0
    
    for i, concept in enumerate(top_65):
        # 1 to 35: 2 marks. 36 to 65: 1 mark.
        marks = 2 if i < 35 else 1
        
        spec_item = {
            "question_number": i + 1,
            "subject": concept["subject"],
            "topic": concept["topic"],
            "concept": concept["concept"],
            "marks": marks,
            "forecast_probability": concept["probability"],
            "confidence": concept["confidence"],
            "evidence_strength": concept.get("evidence_strength", "Moderate")
        }
        
        paper_spec.append(spec_item)
        total_marks += marks
        total_questions += 1
        
    print(f"Generated Paper Spec with {total_questions} questions and {total_marks} marks.")
    
    # VALIDATION
    failures = 0
    def assert_test(name, condition, error_msg):
        nonlocal failures
        if condition:
            print(f"[PASS] {name}")
        else:
            print(f"[FAIL] {name}: {error_msg}")
            failures += 1
            
    assert_test("Exactly 65 Questions", total_questions == 65, f"Expected 65, got {total_questions}")
    assert_test("Exactly 100 Marks", total_marks == 100, f"Expected 100, got {total_marks}")
    
    if failures == 0:
        print("\nSUCCESS: Forecast Specification passed all structural constraints.")
        
        final_output = {
            "metadata": {
                "target_year": forecast_data["metadata"]["target_year"],
                "type": "Level 4 Forecasted Paper Specification",
                "total_questions": total_questions,
                "total_marks": total_marks,
                "generated_at": datetime.now().isoformat()
            },
            "paper_specification": paper_spec
        }
        
        with open(OUTPUT_PATH, "w") as f:
            json.dump(final_output, f, indent=4)
            
        print(f"Saved verified paper specification to {OUTPUT_PATH}")
    else:
        print("\nERROR: Paper specification failed validation.")
        
if __name__ == "__main__":
    run_paper_validator()
