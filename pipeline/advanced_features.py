import pandas as pd
from typing import Dict

class AdvancedFeatureEngineer:
    def __init__(self, history: Dict[str, pd.DataFrame]):
        self.history = history

    def build_budget_features(self, target_year: int, level: str) -> pd.DataFrame:
        """
        Calculates budget features based on the historical subject/topic mark allocations.
        Uses EMA over historical years to predict expected budget.
        """
        marks = self.history.get("marks", pd.DataFrame())
        if marks.empty:
            return pd.DataFrame()
            
        # For this skeleton, we assume 'marks' matrix is already aggregated at the requested level.
        # Ideally, this would query the DB to get Subject -> Topic -> Subtopic hierarchy.
        
        # Calculate EMA of marks for each entity
        ema_marks = marks.ewm(span=5, adjust=False).mean().iloc[-1]
        
        features = pd.DataFrame(index=marks.columns)
        features['expected_budget_marks'] = ema_marks
        
        # Share of total budget
        total_expected = ema_marks.sum()
        features['expected_budget_share'] = ema_marks / total_expected if total_expected > 0 else 0
        
        return features
