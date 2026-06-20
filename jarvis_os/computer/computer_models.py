from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ProcessInfo(BaseModel):
    pid: int
    name: str
    memory_percent: float
    cpu_percent: float

class CPUInfo(BaseModel):
    percent: float
    core_count: int

class MemoryInfo(BaseModel):
    total_gb: float
    used_gb: float
    percent: float

class DiskInfo(BaseModel):
    total_gb: float
    used_gb: float
    percent: float

class BatteryInfo(BaseModel):
    percent: float
    power_plugged: bool
    exists: bool

class NetworkInfo(BaseModel):
    is_connected: bool
    active_interfaces: int

class SystemInfo(BaseModel):
    os_name: str
    os_version: str
    machine: str
    time: str

class ComputerSnapshot(BaseModel):
    system: SystemInfo
    cpu: CPUInfo
    memory: MemoryInfo
    disk: DiskInfo
    battery: BatteryInfo
    network: NetworkInfo
    applications: List[ProcessInfo]
    
class AnalysisResult(BaseModel):
    state_flags: List[str]
    summary: str
