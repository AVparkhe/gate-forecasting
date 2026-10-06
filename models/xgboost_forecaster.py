import pandas as pd
from typing import Dict, Any
import xgboost as xgb

class XGBoostForecaster:
    def __init__(self, use_semantic: bool = False, **kwargs):
        self.use_semantic = use_semantic
        # Default hyperparameters, can be overridden by **kwargs from tuner
        self.model = xgb.XGBClassifier(eval_metric='logloss', random_state=42, **kwargs)
        
    def train(self, X_train: pd.DataFrame, y_train: pd.Series):
        """Train the model on historical features and actuals."""
        self.model.fit(X_train, y_train)
        
    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        Return DataFrame with 'probability', 'expected_marks', 'expected_count'
        """
        preds = pd.DataFrame(index=features.index)
        
        if not features.empty and self.model is not None:
            # Predict probabilities for the positive class
            probas = self.model.predict_proba(features)
            preds['probability'] = probas[:, 1] if probas.shape[1] > 1 else 0.0
        else:
            preds['probability'] = 0.0
            
        preds['expected_marks'] = features.get('avg_marks_when_present', 1.0) * preds['probability']
        preds['expected_count'] = preds['probability']
        
        return preds
