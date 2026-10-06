import pandas as pd
import numpy as np
from typing import Dict, Any, List
from sklearn.metrics import f1_score

class TimeSeriesHyperparameterTuner:
    """
    Implements nested temporal cross-validation for time series forecasting models.
    Ensures that validation sets are always strictly in the future of training sets,
    preventing data leakage.
    """
    def __init__(self, n_splits: int = 3):
        self.n_splits = n_splits
        
    def tune(self, df: pd.DataFrame, target_col: str, model_class, param_grid: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        df must contain a 'year' column to split temporally.
        """
        if 'year' not in df.columns:
            raise ValueError("DataFrame must contain a 'year' column for temporal cross-validation.")
            
        years = sorted(df['year'].unique())
        if len(years) < self.n_splits + 1:
            # Not enough years for splits, return first param set
            return param_grid[0]
            
        best_param = None
        best_score = -1.0
        
        for params in param_grid:
            scores = []
            for i in range(len(years) - self.n_splits, len(years)):
                train_years = years[:i]
                val_year = years[i]
                
                train_df = df[df['year'].isin(train_years)]
                val_df = df[df['year'] == val_year]
                
                if train_df.empty or val_df.empty:
                    continue
                    
                X_train = train_df.drop(columns=[target_col, 'year'])
                y_train = train_df[target_col]
                
                X_val = val_df.drop(columns=[target_col, 'year'])
                y_val = val_df[target_col]
                
                model = model_class(**params)
                model.train(X_train, y_train)
                
                preds = model.predict(X_val)
                # Assume preds has 'probability'
                y_pred_class = (preds['probability'] > 0.5).astype(int)
                
                score = f1_score(y_val, y_pred_class, zero_division=0)
                scores.append(score)
                
            avg_score = np.mean(scores) if scores else 0
            if avg_score > best_score:
                best_score = avg_score
                best_param = params
                
        return best_param if best_param is not None else param_grid[0]
