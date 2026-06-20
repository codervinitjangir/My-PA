from pydantic import BaseModel
from typing import List, Dict

class OperatorHealth(BaseModel):
    available_modules: List[str]
    failed_modules: List[str]
    disabled_modules: List[str]

class RoutePlan(BaseModel):
    intent: str
    target_modules: List[str]
