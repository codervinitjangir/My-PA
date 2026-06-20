from typing import Dict, Any
import time

class GlobalStateManager:
    """
    Aggregates the current status of all ACTIVE state-bearing capabilities
    to provide the LLM parser a single, unified context payload.
    """
    def __init__(self):
        # In a real environment, these would be populated by the CapabilityRegistry or active instances
        self.mock_states = {
            "identity": {"boss": "LENOVO", "trust_level": "high"},
            "session": {"active_session": "Jarvis OS Refactor", "pending": 4},
            "awareness": {"focus": "Consolidation", "projects": ["Jarvis"]},
            "computer": {"cpu": "14%", "memory": "42%", "os": "Windows"},
            "recommendation": ["Complete core interfaces", "Generate reports"],
            "desktop_state": "idle",
            "memory": {"last_action": "created task.md", "timestamp": time.time()},
            "digital_activity": {"activity": "Building", "focus_drift": False},
            "workspace": {
                "current": {"name": "Jarvis", "tools": ["VS Code", "Terminal"]},
                "suggested": {"name": "Vision", "tools": ["Notion", "Browser"]}
            },
            "screen": None,  # Populated on-demand by ScreenObserver
        }

    def update_runtime_state(self, key: str, value: Any) -> None:
        """Update a single runtime key. Used for on-demand state (e.g. screen)."""
        self.mock_states[key] = value

    def build_global_state(self) -> Dict[str, Any]:
        return {
            "timestamp": time.time(),
            "identity": self.mock_states.get("identity"),
            "session": self.mock_states.get("session"),
            "awareness": self.mock_states.get("awareness"),
            "computer": self.mock_states.get("computer"),
            "recommendation": self.mock_states.get("recommendation"),
            "desktop_state": self.mock_states.get("desktop_state"),
            "memory": self.mock_states.get("memory"),
            "digital_activity": self.mock_states.get("digital_activity"),
            "workspace": self.mock_states.get("workspace"),
            "screen": self.mock_states.get("screen"),
        }
