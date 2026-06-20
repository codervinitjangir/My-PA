from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Profile(BaseModel):
    name: str
    nickname: str
    education: str
    skills: List[str]
    experience: str
    location: Optional[str]
    profession: str
    interests: List[str]
    assistant_name: str
    assistant_personality: str

class Preferences(BaseModel):
    communication_style: str
    working_style: str
    coding_style: str
    sleep_schedule: str
    study_preferences: str
    favorite_tools: List[str]
    language_preferences: List[str]
    notification_preferences: str

class Device(BaseModel):
    device_name: str
    device_type: str
    os: str
    status: str
    purpose: str

class Goals(BaseModel):
    short_term_goals: List[str]
    long_term_goals: List[str]
    active_goals: List[str]
    completed_goals: List[str]

class Project(BaseModel):
    project_name: str
    description: str
    priority: str
    status: str
    technologies: List[str]
    deadlines: str

class Relationship(BaseModel):
    name: str
    relationship_type: str
    importance: str
    notes: str
