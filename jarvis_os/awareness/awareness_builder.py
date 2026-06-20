from typing import Dict, Any, List

class AwarenessBuilder:
    """
    Builds the structured Self-Awareness state.
    Aggregates inputs into a single cohesive dictionary.
    """
    def build_awareness_state(
        self,
        boss_state: Dict[str, Any],
        active_projects: List[Dict[str, Any]],
        active_goals: List[Dict[str, Any]],
        urgent_items: List[Dict[str, Any]],
        pending_items: List[Dict[str, Any]],
        suggestions: List[str]
    ) -> Dict[str, Any]:
        
        # Determine current focus based on goals or projects
        current_focus = "General"
        for goal in active_goals:
            if goal.get("status") == "in_progress":
                current_focus = goal.get("name", current_focus)
                break
                
        if current_focus == "General" and boss_state.get("is_coding"):
            current_focus = "Coding Session"

        return {
            "boss_state": boss_state,
            "active_projects": active_projects,
            "active_goals": active_goals,
            "current_focus": current_focus,
            "urgent_items": urgent_items,
            "pending_items": pending_items,
            "suggestions": suggestions
        }
