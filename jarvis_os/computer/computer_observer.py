import psutil
import platform
import socket
from datetime import datetime
from typing import List, Dict, Any

class ComputerObserver:
    """
    OBSERVATION ONLY. NO CONTROL.
    Reads hardware sensors and OS states safely using psutil.
    """
    def get_system_info(self) -> Dict[str, str]:
        return {
            "os_name": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "time": self.get_current_time()
        }

    def get_cpu_usage(self) -> Dict[str, Any]:
        return {
            "percent": psutil.cpu_percent(interval=0.1),
            "core_count": psutil.cpu_count(logical=True)
        }

    def get_memory_usage(self) -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent
        }

    def get_disk_usage(self) -> Dict[str, Any]:
        disk = psutil.disk_usage('/')
        return {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "percent": disk.percent
        }

    def get_network_status(self) -> Dict[str, Any]:
        # Fast check using socket
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=1)
            is_connected = True
        except OSError:
            is_connected = False
            
        stats = psutil.net_if_stats()
        active_interfaces = sum(1 for name, stat in stats.items() if stat.isup)
        
        return {
            "is_connected": is_connected,
            "active_interfaces": active_interfaces
        }

    def get_battery_status(self) -> Dict[str, Any]:
        battery = psutil.sensors_battery()
        if battery:
            return {
                "percent": battery.percent,
                "power_plugged": battery.power_plugged,
                "exists": True
            }
        return {
            "percent": 100.0,
            "power_plugged": True,
            "exists": False
        }

    def get_running_applications(self) -> List[Dict[str, Any]]:
        apps = []
        try:
            # We filter top memory consuming processes to avoid huge lists
            procs = [p.info for p in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent'])]
            procs = sorted(procs, key=lambda p: p.get('memory_percent', 0) or 0, reverse=True)
            for p in procs[:10]:  # Top 10 apps
                apps.append({
                    "pid": p['pid'],
                    "name": p['name'],
                    "memory_percent": round(p['memory_percent'] or 0, 1),
                    "cpu_percent": round(p['cpu_percent'] or 0, 1)
                })
        except Exception:
            pass
        return apps

    def get_current_time(self) -> str:
        return datetime.now().isoformat()

    def get_desktop_environment(self) -> str:
        import os
        return os.environ.get('DESKTOP_SESSION', platform.system())
