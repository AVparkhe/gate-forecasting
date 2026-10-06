import pandas as pd
from typing import Dict

class EnsembleForecaster:
    """
    Blends the predictions of multiple models (e.g., EMA + XGBoost).
    """
    def __init__(self, weights: Dict[str, float]):
        self.weights = weights
        
    def blend(self, predictions: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        predictions: mapping of model_name to its predicted DataFrame 
        Returns blended predictions.
        """
        blended_probas = None
        
        total_weight = sum(self.weights.values())
        normalized_weights = {k: v / total_weight for k, v in self.weights.items()}
        
        for model_name, preds in predictions.items():
            if model_name not in normalized_weights:
                continue
                
            w = normalized_weights[model_name]
            if blended_probas is None:
                blended_probas = preds['probability'] * w
            else:
                blended_probas += preds['probability'] * w
                
        # Create output dataframe based on the first model's index
        first_preds = list(predictions.values())[0]
        final_preds = pd.DataFrame(index=first_preds.index)
        final_preds['probability'] = blended_probas
        
        marks_sum = None
        for model_name, preds in predictions.items():
            if model_name not in normalized_weights:
                continue
            w = normalized_weights[model_name]
            if 'expected_marks' in preds.columns:
                val = preds['expected_marks']
            else:
                val = preds['probability']
            if marks_sum is None:
                marks_sum = val * w
            else:
                marks_sum += val * w
                
        final_preds['expected_marks'] = marks_sum
        final_preds['expected_count'] = final_preds['probability']
        
        return final_preds
