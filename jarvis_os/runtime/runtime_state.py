from pydantic import BaseModel
from typing import List

class RuntimeState(BaseModel):
    current_focus: str = "Integrating and testing the Jarvis OS Runtime layer."
    active_goals: List[str] = [
        "Provide contextual awareness without increasing latency.",
        "Ensure prompt responses stay within 400-500 words of injected context."
    ]
    active_projects: List[str] = [
        "Week 2.5 Real MVP Integration",
        "Jarvis OS Architecture"
    ]
    current_priorities: List[str] = [
        "Stability of MVP",
        "Accuracy of Context Injection"
    ]
