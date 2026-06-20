from pydantic import BaseModel
from typing import List, Dict

class TestResult(BaseModel):
    scenario_name: str
    expected_modules: List[str]
    routed_modules: List[str]
    success: bool
    latency_ms: int

class SystemHealth(BaseModel):
    healthy_modules: List[str]
    degraded_modules: List[str]
    unused_modules: List[str]
    missing_connections: List[str]
