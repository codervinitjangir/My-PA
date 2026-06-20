from typing import Dict, Any, List
from jarvis_os.recommendation.recommendation_builder import RecommendationBuilder
from jarvis_os.recommendation.recommendation_prioritizer import RecommendationPrioritizer
from jarvis_os.recommendation.recommendation_history import RecommendationHistory
from jarvis_os.recommendation.recommendation_models import Recommendation

class RecommendationManager:
    """
    Central node for generating proactive recommendations.
    Transforms JARVIS from reactive to proactive, safely.
    """
    def __init__(self):
        self.builder = RecommendationBuilder()
        self.prioritizer = RecommendationPrioritizer()
        self.history = RecommendationHistory()
        
    def generate_recommendations(self, full_state: Dict[str, Any]) -> List[Recommendation]:
        """
        Generates and prioritizes a list of recommendations without executing anything.
        """
        raw_recs = self.builder.build_recommendations(full_state)
        
        # Filter out spam
        filtered = [r for r in raw_recs if not self.history.was_recently_recommended(r.action_required)]
        
        # Prioritize
        top_recs = self.prioritizer.prioritize(filtered)
        
        # Log to history
        for rec in top_recs:
            self.history.log_recommendation(rec)
            
        return top_recs
        
    def build_action_request(self, recommendation: Recommendation) -> str:
        """
        The Ask Layer: Translates a recommendation into a permission request.
        """
        action_text = recommendation.action_required.replace('_', ' ')
        return f"I recommend {action_text}. Reason: {recommendation.reason} Proceed?"
