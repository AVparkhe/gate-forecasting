import pandas as pd
import numpy as np
from typing import Dict

class FeatureEngineer:
    def __init__(self, history_matrices: Dict[str, pd.DataFrame]):
        """
        Takes the safe history matrices (appearance, count, marks) 
        up to T-1 and engineers features for predicting T.
        """
        self.appearance = history_matrices.get("appearance", pd.DataFrame())
        self.count = history_matrices.get("count", pd.DataFrame())
        self.marks = history_matrices.get("marks", pd.DataFrame())

    def build_features(self, target_year: int) -> pd.DataFrame:
        if self.appearance.empty:
            return pd.DataFrame()
            
        features = []
        entities = self.appearance.columns
        
        # We assume the index of the dataframe is the year, sorted
        years = self.appearance.index.sort_values().tolist()
        if not years:
            return pd.DataFrame()
            
        current_year = target_year
        
        for entity in entities:
            app_series = self.appearance[entity]
            count_series = self.count[entity]
            marks_series = self.marks[entity]
            
            # Basic stats
            total_appearances = app_series.sum()
            total_marks = marks_series.sum()
            avg_marks_when_present = (marks_series[app_series > 0].mean()) if total_appearances > 0 else 0
            
            # Recency
            seen_years = app_series[app_series > 0].index.tolist()
            last_seen_year = seen_years[-1] if seen_years else 0
            years_since_last_seen = (current_year - last_seen_year) if last_seen_year else 999
            
            # Rolling frequency (e.g. last 3, 5, 10 years)
            last_3 = app_series[app_series.index >= (current_year - 3)].sum()
            last_5 = app_series[app_series.index >= (current_year - 5)].sum()
            last_10 = app_series[app_series.index >= (current_year - 10)].sum()
            
            # Gap
            if len(seen_years) > 1:
                gaps = np.diff(seen_years)
                longest_gap = gaps.max()
            else:
                longest_gap = years_since_last_seen
                
            # Volatility
            variance = marks_series.var() if len(marks_series) > 1 else 0
            
            features.append({
                "entity": entity,
                "total_appearances": total_appearances,
                "total_marks": total_marks,
                "avg_marks_when_present": avg_marks_when_present,
                "years_since_last_seen": years_since_last_seen,
                "last_seen_year": last_seen_year,
                "last_3_freq": last_3,
                "last_5_freq": last_5,
                "last_10_freq": last_10,
                "longest_gap": longest_gap,
                "volatility": variance
            })
            
        df_features = pd.DataFrame(features)
        df_features.set_index("entity", inplace=True)
        return df_features
