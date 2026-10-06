import pandas as pd

class RankingEngine:
    @staticmethod
    def rank_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a dataframe with 'probability' and 'expected_marks'.
        Ranks entities primarily by probability, then by expected marks.
        Assigns confidence tiers.
        """
        if predictions.empty:
            return predictions
            
        # Sort descending
        ranked = predictions.sort_values(by=['probability', 'expected_marks'], ascending=[False, False]).copy()
        
        # Assign rank
        ranked['predicted_rank'] = range(1, len(ranked) + 1)
        
        # Assign confidence tier
        def get_tier(prob):
            if prob >= 0.75:
                return 'HIGH'
            elif prob >= 0.40:
                return 'MEDIUM'
            else:
                return 'LOW'
                
        ranked['confidence_tier'] = ranked['probability'].apply(get_tier)
        
        return ranked
