import pandas as pd
from typing import Dict

class TimeSeriesBuilder:
    def __init__(self, target_matrices: Dict[str, pd.DataFrame]):
        """
        target_matrices is the output of TargetBuilder.build_matrices()
        {"appearance": df, "count": df, "marks": df}
        """
        self.matrices = target_matrices

    def get_history_up_to(self, target_year: int) -> Dict[str, pd.DataFrame]:
        """
        Returns the matrices strictly filtered to years <= target_year - 1.
        This PREVENTS DATA LEAKAGE during walk-forward validation.
        """
        safe_matrices = {}
        for key, df in self.matrices.items():
            if df.empty:
                safe_matrices[key] = pd.DataFrame()
            else:
                # Keep only rows where the index (exam_year) is < target_year
                safe_df = df[df.index < target_year].copy()
                safe_matrices[key] = safe_df
        return safe_matrices
