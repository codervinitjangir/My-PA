class OperatorRegistry:
    """
    Tracks all registered components of JARVIS OS.
    """
    def __init__(self):
        self.modules = {
            "identity": True,
            "memory": True,
            "awareness": True,
            "computer": True,
            "session": True,
            "decision": True,
            "planner": True,
            "recommendation": True,
            "desktop_action": True
        }
        
    def get_health(self) -> dict:
        available = [m for m, active in self.modules.items() if active]
        disabled = [m for m, active in self.modules.items() if not active]
        return {
            "available_modules": available,
            "failed_modules": [],
            "disabled_modules": disabled
        }
