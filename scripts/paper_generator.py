import sqlite3
import random
import uuid
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class ConstraintBasedPaperGenerator:
    """
    Phase 6: Dynamically learns paper format constraints and generates a structurally 
    valid predicted paper based on historical probabilities without duplicate stuffing.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_historical_constraints(self, target_year: int) -> Dict[str, Any]:
        """
        Learns constraints from data prior to target_year.
        """
        cursor = self.conn.cursor()
        # Fetching historical marks distribution per subject
        cursor.execute("""
            SELECT go_subject, SUM(marks) as total_marks, COUNT(*) as q_count 
            FROM golden_questions 
            WHERE exam_year < ? AND go_subject IS NOT NULL
            GROUP BY go_subject
        """, (target_year,))
        
        subject_stats = cursor.fetchall()
        
        # Calculate total historical years to find average per year
        cursor.execute("SELECT COUNT(DISTINCT exam_year) FROM golden_questions WHERE exam_year < ?", (target_year,))
        years_count = cursor.fetchone()[0] or 1
        
        budget = {}
        total_paper_marks = 100
        
        for row in subject_stats:
            avg_marks = row['total_marks'] / years_count
            budget[row['go_subject']] = {
                'expected_marks': avg_marks,
                'allocated': 0
            }
            
        return {
            'total_marks': total_paper_marks,
            'subject_budget': budget,
            'max_questions': 65
        }

    def generate_predicted_paper(self, predictions: List[Dict[str, Any]], target_year: int) -> List[Dict[str, Any]]:
        """
        Generates a valid paper from a list of concept probabilities.
        """
        constraints = self.get_historical_constraints(target_year)
        budget = constraints['subject_budget']
        
        # Sort predictions by probability descending
        sorted_preds = sorted(predictions, key=lambda x: x.get('probability', 0.0), reverse=True)
        
        predicted_paper = []
        current_marks = 0
        used_concepts = set()
        
        for pred in sorted_preds:
            if current_marks >= constraints['total_marks'] or len(predicted_paper) >= constraints['max_questions']:
                break
                
            subject = pred.get('subject')
            concept = pred.get('concept')
            marks = float(pred.get('marks', 2.0))
            
            if concept in used_concepts:
                continue # Prevent duplicate concept stuffing
                
            # Check subject budget
            subj_constraints = budget.get(subject, {'expected_marks': 10.0, 'allocated': 0})
            
            # Allow slight over-allocation (e.g. 15% tolerance)
            if subj_constraints['allocated'] + marks <= subj_constraints['expected_marks'] * 1.15:
                # Accept this question
                predicted_paper.append({
                    'prediction_id': str(uuid.uuid4()),
                    'subject': subject,
                    'topic': pred.get('topic'),
                    'subtopic': pred.get('subtopic'),
                    'concept': concept,
                    'marks': marks,
                    'question_type': pred.get('question_type', 'MCQ'),
                    'difficulty': pred.get('difficulty', 'Medium'),
                    'probability': pred.get('probability'),
                    'confidence': 'High' if pred.get('probability', 0) > 0.8 else 'Medium'
                })
                
                current_marks += marks
                subj_constraints['allocated'] += marks
                used_concepts.add(concept)
                
        logger.info(f"Generated paper for {target_year} with {len(predicted_paper)} questions and {current_marks} marks.")
        return predicted_paper

    def close(self):
        self.conn.close()

if __name__ == "__main__":
    from config.settings import DB_PATH
    generator = ConstraintBasedPaperGenerator(DB_PATH)
    constraints = generator.get_historical_constraints(2020)
    print("Learned Subject Budget for 2020:")
    for subj, c in constraints['subject_budget'].items():
        print(f"  {subj}: ~{c['expected_marks']:.1f} marks")
    generator.close()
