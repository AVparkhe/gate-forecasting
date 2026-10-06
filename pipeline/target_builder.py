import sqlite3
import pandas as pd
from typing import Dict, Any

class TargetBuilder:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def _fetch_enriched_data(self) -> pd.DataFrame:
        """Fetch all enriched golden questions joined with their enrichment data."""
        query = """
        SELECT q.golden_question_id, q.exam_year, q.marks, 
               e.ai_subject, e.ai_topic, e.ai_subtopic, e.core_concepts
        FROM golden_questions q
        JOIN question_enrichment e ON q.golden_question_id = e.golden_question_id
        WHERE e.validation_status = 'VALID'
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn)
        return df

    def build_matrices(self, level: str) -> Dict[str, pd.DataFrame]:
        """
        Builds three matrices for the given hierarchical level:
        - Appearance (0 or 1)
        - Question Count
        - Marks
        
        level can be: 'SUBJECT', 'TOPIC', 'SUBTOPIC', 'CONCEPT'
        """
        df = self._fetch_enriched_data()
        if df.empty:
            return {"appearance": pd.DataFrame(), "count": pd.DataFrame(), "marks": pd.DataFrame()}
            
        # Explode logic based on level
        if level == 'SUBJECT':
            df['entity'] = df['ai_subject']
        elif level == 'TOPIC':
            df['entity'] = df['ai_topic']
        elif level == 'SUBTOPIC':
            df['entity'] = df['ai_subtopic']
        elif level == 'CONCEPT':
            # core_concepts is JSON string, need to parse and explode
            import json
            def extract_concepts(c_str):
                try:
                    c_list = json.loads(c_str)
                    return [c['name'] for c in c_list] if c_list else []
                except:
                    return []
            df['entity'] = df['core_concepts'].apply(extract_concepts)
            df = df.explode('entity')
        else:
            raise ValueError(f"Unknown level: {level}")
            
        # Drop rows where entity is missing
        df = df.dropna(subset=['entity'])
        if df.empty:
            return {"appearance": pd.DataFrame(), "count": pd.DataFrame(), "marks": pd.DataFrame()}

        # Aggregate by exam_year and entity
        agg = df.groupby(['exam_year', 'entity']).agg(
            q_count=('golden_question_id', 'count'),
            total_marks=('marks', 'sum')
        ).reset_index()

        # Pivot to create Year x Entity matrices
        count_matrix = agg.pivot(index='exam_year', columns='entity', values='q_count').fillna(0)
        marks_matrix = agg.pivot(index='exam_year', columns='entity', values='total_marks').fillna(0)
        appearance_matrix = (count_matrix > 0).astype(int)

        return {
            "appearance": appearance_matrix,
            "count": count_matrix,
            "marks": marks_matrix
        }
