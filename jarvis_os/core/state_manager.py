import os
from typing import Dict, Any
import time

class GlobalStateManager:
    """
    Single source of truth for system state context.
    Identity fields are driven by .env vars (JARVIS_OWNER_NAME, JARVIS_USER_TITLE).
    Perf-sensitive data (CPU, memory) uses lightweight defaults unless psutil is available.
    Screen state is populated on-demand by ScreenObserver via update_runtime_state().
    """
    def __init__(self):
        # Identity from env — not hardcoded
        owner = os.getenv("JARVIS_OWNER_NAME", "Boss")
        title = os.getenv("JARVIS_USER_TITLE", "Boss")
        assistant = os.getenv("ASSISTANT_NAME", "Jarvis")

        # Try to get live CPU/memory; fall back gracefully
        cpu, mem = self._get_system_stats()

        self._static = {
            "identity": {"boss": title, "owner": owner, "assistant": assistant, "trust_level": "high"},
            "computer": {"cpu": cpu, "memory": mem, "os": "Windows"},
            "desktop_state": "idle",
        }
        # Runtime state — updated dynamically
        self._runtime: Dict[str, Any] = {
            "screen": None,
        }

    @staticmethod
    def _get_system_stats() -> tuple:
        """Returns (cpu_str, mem_str). Uses psutil if available, else returns placeholders."""
        try:
            import psutil
            cpu = f"{psutil.cpu_percent(interval=None):.0f}%"
            mem = f"{psutil.virtual_memory().percent:.0f}%"
            return cpu, mem
        except ImportError:
            return "—", "—"

    def update_runtime_state(self, key: str, value: Any) -> None:
        """Update a single runtime key (e.g. screen state from ScreenObserver)."""
        self._runtime[key] = value

    def build_global_state(self) -> Dict[str, Any]:
        return {
            "timestamp": time.time(),
            "identity": self._static["identity"],
            "computer": self._static["computer"],
            "desktop_state": self._static["desktop_state"],
            "screen": self._runtime.get("screen"),
            # Flat keys expected by DashboardBuilder
            "current_focus": "No active focus set",
            "active_project": "No active project",
            "pending_items": 0,
            "recommendations": [],
            "digital_activity": self._runtime.get("digital_activity"),
            "workspace": self._runtime.get("workspace"),
        }
