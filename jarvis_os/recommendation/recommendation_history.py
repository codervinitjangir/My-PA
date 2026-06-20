from typing import List
from jarvis_os.recommendation.recommendation_models import Recommendation
from datetime import datetime

class RecommendationHistory:
    """
    Tracks what has been recommended to avoid spamming the user.
    """
    def __init__(self):
        self.history = []
        
    def log_recommendation(self, rec: Recommendation):
        self.history.append({
            "timestamp": datetime.now(),
            "recommendation": rec.dict()
        })
        
    def was_recently_recommended(self, action_required: str, hours: int = 4) -> bool:
        now = datetime.now()
        for entry in reversed(self.history):
            delta = now - entry["timestamp"]
            if delta.total_seconds() > hours * 3600:
                break
            if entry["recommendation"]["action_required"] == action_required:
                return True
        return False
