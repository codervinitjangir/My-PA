from pydantic import BaseModel
from typing import List, Optional

class ComputerSummary(BaseModel):
    os: str
    cpu_usage: str
    memory_usage: str

class DashboardState(BaseModel):
    greeting: str
    current_focus: str
    active_project: str
    pending_items: int
    recommendations: List[str]
    computer_summary: ComputerSummary
    session_summary: str
    time_of_day: str
    timeline: dict
    digital_activity: Optional[dict] = None
    workspace: Optional[dict] = None
    current_screen: Optional[dict] = None
    telegram_enabled: bool = False
