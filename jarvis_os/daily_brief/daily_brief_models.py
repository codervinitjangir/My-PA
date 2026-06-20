from pydantic import BaseModel
from typing import List

class BriefingState(BaseModel):
    greeting: str
    today_focus: str
    active_projects: List[str]
    pending_tasks: int
    recommendations: List[str]
    computer_status: str
    suggested_action: str
    energy_score: str
    today_mode: str
