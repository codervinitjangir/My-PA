from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

def _generate_id():
    return str(uuid.uuid4())

def _now():
    return datetime.utcnow().isoformat()

class Task(BaseModel):
    id: str = Field(default_factory=_generate_id)
    title: str
    description: str
    priority: str = "medium"
    status: str = "pending"
    dependencies: List[str] = []
    estimated_time: str = "30m"
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)

class SubGoal(BaseModel):
    id: str = Field(default_factory=_generate_id)
    title: str
    description: str
    priority: str = "medium"
    status: str = "pending"
    dependencies: List[str] = []
    estimated_time: str = "2h"
    tasks: List[Task] = []
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)

class Goal(BaseModel):
    id: str = Field(default_factory=_generate_id)
    title: str
    description: str
    priority: str = "medium"
    status: str = "pending"
    dependencies: List[str] = []
    estimated_time: str = "1w"
    subgoals: List[SubGoal] = []
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)

class Plan(BaseModel):
    id: str = Field(default_factory=_generate_id)
    title: str
    description: str
    priority: str = "medium"
    status: str = "active"
    dependencies: List[str] = []
    estimated_time: str = "1w"
    ordered_tasks: List[Task] = []
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)
