from enum import Enum
from pydantic import BaseModel
from typing import Optional
import time

class ActivityType(str, Enum):
    BUILDING = "Building"
    JOB_SEARCH = "Job Search"
    LEARNING = "Learning"
    RESEARCH = "Research"
    ENTERTAINMENT = "Entertainment"
    COMMUNICATION = "Communication"
    SOCIAL = "Social"
    IDLE = "Idle"
    UNKNOWN = "Unknown"

class DigitalActivity(BaseModel):
    activity: ActivityType
    confidence: float
    source: str
    timestamp: float
    focus_drift: bool

class ScreenActivityType(str, Enum):
    CODING = "Coding"
    DEBUGGING = "Debugging"
    LEARNING = "Learning"
    RESEARCH = "Research"
    JOB_SEARCH = "Job Search"
    DESIGNING = "Designing"
    COMMUNICATION = "Communication"
    ENTERTAINMENT = "Entertainment"
    UNKNOWN = "Unknown"

class ScreenState(BaseModel):
    application: str
    activity: ScreenActivityType
    confidence: float           # 0-100 deterministic
    summary: str
    next_best_action: str
    timestamp: float
