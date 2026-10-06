import pandas as pd
from typing import Dict, Any

class BaselineModels:
    @staticmethod
    def historical_frequency(features: pd.DataFrame, total_historical_years: int) -> pd.DataFrame:
        """
        P(topic) = total appearances / total years
        Expected marks = total marks / total years
        """
        preds = pd.DataFrame(index=features.index)
        if total_historical_years > 0:
            preds['probability'] = features['total_appearances'] / total_historical_years
            preds['expected_marks'] = features['total_marks'] / total_historical_years
            preds['expected_count'] = features['total_appearances'] / total_historical_years
        else:
            preds['probability'] = 0.0
            preds['expected_marks'] = 0.0
            preds['expected_count'] = 0.0
        return preds

    @staticmethod
    def recent_frequency(features: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """
        P(topic) = appearances in last `window` years / `window`
        """
        preds = pd.DataFrame(index=features.index)
        col_name = f"last_{window}_freq"
        if col_name in features.columns:
            preds['probability'] = features[col_name] / window
            # Approx marks based on historical avg when present
            preds['expected_marks'] = preds['probability'] * features['avg_marks_when_present']
            preds['expected_count'] = preds['probability'] * 1.0 # rough estimate
        else:
            preds['probability'] = 0.0
            preds['expected_marks'] = 0.0
            preds['expected_count'] = 0.0
        return preds
