import pandas as pd
import numpy as np
from sklearn.calibration import CalibratedClassifierCV

class ProbabilityCalibrator:
    """
    Applies Isotonic or Platt scaling (Sigmoid) to raw model outputs to produce well-calibrated probabilities.
    """
    def __init__(self, method: str = 'isotonic'):
        """
        method: 'isotonic' or 'sigmoid'
        """
        self.method = method
        self.calibrator = None
        
    def calibrate(self, model, X_val: pd.DataFrame, y_val: pd.Series):
        """
        Fits the calibrator on a validation set. 
        model must be a fitted classifier or follow sklearn API.
        """
        # Note: CalibratedClassifierCV with cv="prefit" requires the base model to be already fitted.
        self.calibrator = CalibratedClassifierCV(estimator=model, method=self.method, cv="prefit")
        self.calibrator.fit(X_val, y_val)
        
    def predict_calibrated(self, X: pd.DataFrame) -> np.ndarray:
        """
        Returns calibrated probabilities for the positive class.
        """
        if self.calibrator is None:
            raise ValueError("Calibrator has not been fitted. Call calibrate() first.")
        
        probas = self.calibrator.predict_proba(X)
        return probas[:, 1] if probas.shape[1] > 1 else probas[:, 0] * 0.0
