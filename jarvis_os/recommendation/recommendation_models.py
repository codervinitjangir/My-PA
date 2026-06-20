from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class RecommendationCategory(str, Enum):
    FOCUS = "focus"
    WORK = "work"
    STUDY = "study"
    HEALTH = "health"
    SYSTEM = "system"
    PROJECT = "project"
    REMINDER = "reminder"
    OPTIMIZATION = "optimization"

class Recommendation(BaseModel):
    title: str
    reason: str
    priority: int  # 1 (Highest) to 5 (Lowest)
    action_required: str  # Action identifier or description
    category: RecommendationCategory
