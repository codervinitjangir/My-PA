from typing import Dict, Any, List
from jarvis_os.recommendation.recommendation_models import Recommendation, RecommendationCategory
from datetime import datetime, timedelta

class RecommendationBuilder:
    """
    Deterministic rules engine to generate actionable recommendations based on full OS state.
    NO AI is used here.
    """
    def build_recommendations(self, full_state: Dict[str, Any]) -> List[Recommendation]:
        recs = []
        
        awareness = full_state.get("awareness", {})
        computer = full_state.get("computer", {})
        
        # Rule: Coding session active -> Suppress interruptions
        if awareness.get("boss_state", {}).get("is_coding", False):
            recs.append(Recommendation(
                title="Suppress Interruptions",
                reason="Active coding session detected. Maintaining deep work state.",
                priority=1,
                action_required="enable_dnd",
                category=RecommendationCategory.FOCUS
            ))
            # If coding, we heavily restrict other noisy recommendations
            return recs
            
        # Rule: Memory pressure -> Recommend closing applications
        if "memory_pressure" in computer.get("state_flags", []):
            recs.append(Recommendation(
                title="Free Memory",
                reason="System memory is critically high. Closing unused applications is recommended.",
                priority=2,
                action_required="close_inactive_apps",
                category=RecommendationCategory.SYSTEM
            ))
            
        # Rule: Current focus = Jarvis -> Recommend opening development environment
        current_focus = awareness.get("current_focus", "").lower()
        if "jarvis" in current_focus:
            recs.append(Recommendation(
                title="Open Jarvis Workspace",
                reason="Current focus is set to Jarvis. Prepare the development environment.",
                priority=3,
                action_required="opening_VS_Code_and_the_Jarvis_project_folder",
                category=RecommendationCategory.PROJECT
            ))
            
        # Rule: Interview tomorrow -> Recommend preparation
        for event in awareness.get("pending_items", []):
            title = event.get("title", "").lower()
            date = event.get("date")
            if "interview" in title and date:
                now = datetime.now()
                if 0 <= (date - now).days <= 1:
                    recs.append(Recommendation(
                        title="Interview Preparation",
                        reason=f"Interview '{event.get('title')}' is tomorrow. Recommend reviewing notes.",
                        priority=2,
                        action_required="open_interview_notes",
                        category=RecommendationCategory.WORK
                    ))
                    
        return recs
