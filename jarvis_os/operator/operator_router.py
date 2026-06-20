from typing import List
from jarvis_os.operator.operator_models import RoutePlan

class OperatorRouter:
    """
    Deterministic router. Maps natural intent strings to required execution pipelines.
    No AI involved.
    """
    def route_intent(self, user_input: str) -> RoutePlan:
        intent = user_input.lower()
        
        if "what should i do" in intent or "suggest" in intent:
            return RoutePlan(
                intent="generate_suggestions",
                target_modules=["awareness", "session", "recommendation"]
            )
            
        if "continue" in intent or "resume" in intent:
            return RoutePlan(
                intent="resume_work",
                target_modules=["session", "planner", "recommendation"]
            )
            
        if "pending" in intent:
            return RoutePlan(
                intent="check_pending",
                target_modules=["session", "planner"]
            )
            
        if "open" in intent or "launch" in intent:
            # Check if it's an alias intent, e.g., "open github"
            words = intent.split()
            if len(words) == 2 and words[0] in ["open", "launch"]:
                return RoutePlan(
                    intent="open_site",
                    target_modules=["desktop_action"]
                )
            
            return RoutePlan(
                intent="desktop_execution",
                target_modules=["desktop_action"]
            )
            
        if "search" in intent:
            return RoutePlan(
                intent="web_search",
                target_modules=["web_assistant"]
            )
            
        if "summarize" in intent:
            return RoutePlan(
                intent="web_summarize",
                target_modules=["web_assistant"]
            )
            
        if "project" in intent or "active" in intent:
            return RoutePlan(
                intent="check_projects",
                target_modules=["identity", "awareness"]
            )
            
        return RoutePlan(
            intent="unknown",
            target_modules=["awareness"]
        )
