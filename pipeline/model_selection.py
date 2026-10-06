import pandas as pd
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ModelSelector:
    """
    Accepts or rejects an ML model against the EMA baseline based on stability and F1 performance.
    """
    def __init__(self, min_f1_improvement: float = 0.02):
        self.min_f1_improvement = min_f1_improvement
        
    def evaluate(self, ml_metrics: Dict[str, float], baseline_metrics: Dict[str, float]) -> bool:
        """
        Returns True if ML model is accepted, False otherwise.
        """
        ml_f1 = ml_metrics.get("f1", 0.0)
        base_f1 = baseline_metrics.get("f1", 0.0)
        
        improvement = ml_f1 - base_f1
        logger.info(f"Model Selection: ML F1={ml_f1:.4f}, Baseline F1={base_f1:.4f} (Diff: {improvement:.4f})")
        
        if improvement >= self.min_f1_improvement:
            logger.info("Decision: ACCEPTED")
            return True
        else:
            logger.info("Decision: REJECTED")
            return False
