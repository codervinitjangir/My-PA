from typing import Dict, Any, List
from datetime import datetime, timedelta

class AwarenessSuggester:
    """
    Rules-based Suggestion Engine. No AI used.
    Generates actionable suggestions based on deterministic state rules.
    """
    def generate_suggestions(self, state_inputs: Dict[str, Any]) -> List[str]:
        suggestions = []
        
        boss_state = state_inputs.get("boss_state", {})
        active_projects = state_inputs.get("active_projects", [])
        upcoming_events = state_inputs.get("upcoming_events", [])
        
        # Rule: If coding session active -> Do not interrupt
        if boss_state.get("is_coding", False):
            return ["Boss is in an active coding session. Do not interrupt."]
            
        # Rule: If project inactive -> Suggest revisit
        now = datetime.now()
        for proj in active_projects:
            last_active = proj.get("last_active")
            if last_active and (now - last_active).days >= 7:
                suggestions.append(f"Project '{proj.get('name')}' has been inactive for a week. Suggest revisit.")
                
        # Rule: If interview tomorrow -> Suggest preparation
        for event in upcoming_events:
            event_date = event.get("date")
            if event_date and 0 <= (event_date - now).days <= 1:
                if "interview" in event.get("title", "").lower():
                    suggestions.append(f"Interview '{event.get('title')}' is tomorrow. Suggest preparation.")
                    
        return suggestions
