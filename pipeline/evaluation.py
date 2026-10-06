import pandas as pd
import numpy as np

class Evaluator:
    @staticmethod
    def evaluate(predictions: pd.DataFrame, actuals: pd.Series, actual_marks: pd.Series) -> dict:
        """
        predictions: DataFrame with 'probability', 'expected_marks', 'predicted_rank'
        actuals: Series where index is entity, value is 1 if appeared else 0
        actual_marks: Series where index is entity, value is actual marks
        """
        merged = predictions.join(actuals.rename('actual_app')).join(actual_marks.rename('actual_marks')).fillna(0)
        
        metrics = {}
        
        # Top 5 / Top 10 Metrics
        for k in [5, 10]:
            top_k = merged[merged['predicted_rank'] <= k]
            if len(top_k) > 0:
                tp = top_k['actual_app'].sum()
                precision_k = tp / len(top_k)
                total_actual = merged['actual_app'].sum()
                recall_k = tp / total_actual if total_actual > 0 else 0
                
                metrics[f'Precision@{k}'] = precision_k
                metrics[f'Recall@{k}'] = recall_k
            else:
                metrics[f'Precision@{k}'] = 0.0
                metrics[f'Recall@{k}'] = 0.0
                
        # Overall Appearance threshold > 0.5
        preds_binary = (merged['probability'] > 0.5).astype(int)
        tp_total = ((preds_binary == 1) & (merged['actual_app'] > 0)).sum()
        fp = ((preds_binary == 1) & (merged['actual_app'] == 0)).sum()
        fn = ((preds_binary == 0) & (merged['actual_app'] > 0)).sum()
        
        precision = tp_total / (tp_total + fp) if (tp_total + fp) > 0 else 0
        recall = tp_total / (tp_total + fn) if (tp_total + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        metrics['Precision'] = precision
        metrics['Recall'] = recall
        metrics['F1'] = f1
        
        # Marks MAE
        mae = np.abs(merged['expected_marks'] - merged['actual_marks']).mean()
        metrics['MAE'] = mae
        
        return metrics
