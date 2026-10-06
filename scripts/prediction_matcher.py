import sqlite3
import uuid
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class PredictionMatcher:
    """
    Phase 6: Compares predicted paper specifications against the actual paper.
    Matches Subject -> Topic -> Subtopic -> Concept -> Marks.
    """
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_actual_paper(self, target_year: int) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT q.golden_question_id, q.marks, q.question_type, 
                   e.ai_subject as subject, e.ai_topic as topic, 
                   e.ai_subtopic as subtopic, e.core_concepts as concept
            FROM golden_questions q
            LEFT JOIN question_enrichment e ON q.golden_question_id = e.golden_question_id
            WHERE q.exam_year = ?
        """, (target_year,))
        return [dict(row) for row in cursor.fetchall()]

    def compare(self, run_id: str, predicted_paper: List[Dict[str, Any]], target_year: int):
        actual_paper = self.get_actual_paper(target_year)
        
        cursor = self.conn.cursor()
        matches_found = 0
        total_predicted = len(predicted_paper)
        
        # Track unmatched actuals to prevent double matching
        unmatched_actuals = actual_paper.copy()
        
        for pred in predicted_paper:
            best_match = None
            best_score = -1
            best_idx = -1
            
            for idx, actual in enumerate(unmatched_actuals):
                score = 0
                if pred.get('subject') and pred.get('subject') == actual.get('subject'):
                    score += 40
                if pred.get('topic') and pred.get('topic') == actual.get('topic'):
                    score += 30
                if pred.get('subtopic') and pred.get('subtopic') == actual.get('subtopic'):
                    score += 20
                if pred.get('marks') and pred.get('marks') == actual.get('marks'):
                    score += 10
                    
                if score > best_score:
                    best_score = score
                    best_match = actual
                    best_idx = idx
            
            match_status = "🔴 Wrong"
            failure_category = "FALSE_POSITIVE"
            if best_score >= 90:
                match_status = "🟢 Strong Match"
                failure_category = None
            elif best_score >= 40:
                match_status = "🟡 Partial Match"
                failure_category = "PARTIAL"
                
            if best_match and best_score >= 40:
                unmatched_actuals.pop(best_idx)
                matches_found += 1
                
            # Insert match result
            match_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO prediction_matches (
                    match_id, run_id, predicted_id, actual_question_id, 
                    subject_match, topic_match, subtopic_match, concept_match, 
                    match_score, match_status, failure_category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_id, run_id, pred.get('prediction_id'), best_match.get('golden_question_id') if best_match else None,
                pred.get('subject'), pred.get('topic'), pred.get('subtopic'), pred.get('concept'),
                best_score, match_status, failure_category
            ))
            
        # Log false negatives (Unmatched actuals)
        for actual in unmatched_actuals:
            match_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO prediction_matches (
                    match_id, run_id, predicted_id, actual_question_id, 
                    subject_match, topic_match, match_status, failure_category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_id, run_id, None, actual.get('golden_question_id'),
                actual.get('subject'), actual.get('topic'), "⚪ Not Predicted", "FALSE_NEGATIVE"
            ))

        self.conn.commit()
        logger.info(f"Comparison complete for {target_year}. {matches_found}/{total_predicted} strong/partial matches.")
        
    def close(self):
        self.conn.close()
