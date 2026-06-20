from typing import List
from jarvis_os.recommendation.recommendation_models import Recommendation

class RecommendationPrioritizer:
    """
    Sorts and filters recommendations to avoid overwhelming the user.
    """
    def prioritize(self, recommendations: List[Recommendation], max_items: int = 3) -> List[Recommendation]:
        # Sort by priority (1 is highest)
        sorted_recs = sorted(recommendations, key=lambda x: x.priority)
        return sorted_recs[:max_items]
