from pydantic import BaseModel
from typing import List, Optional

class Workspace(BaseModel):
    name: str
    description: str
    tools: List[str]
    sessions: List[str]
    pending_items: int
    recent_activity: str
