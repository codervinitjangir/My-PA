class CapabilityRegistry:
    """
    Central registry for all active and planned JARVIS OS abilities.
    This component manages the whitelist of modules the Operator is allowed to route to.
    """
    def __init__(self):
        self.capabilities = {
            # Intelligence & State
            "identity": {"status": "active", "type": "state"},
            "memory": {"status": "active", "type": "state"},
            "session": {"status": "active", "type": "state"},
            "awareness": {"status": "active", "type": "state"},
            
            # Orchestration
            "recommendation": {"status": "active", "type": "orchestration"},
            "decision": {"status": "active", "type": "orchestration"},
            "planner": {"status": "active", "type": "orchestration"},
            
            # Hardware Sensing
            "computer": {"status": "active", "type": "sensor"},
            
            # Physical Execution (Abilities)
            "desktop_action": {"status": "active", "type": "ability"},
            
            # Future Roadmap
            "future_browser": {"status": "planned", "type": "ability"},
            "future_screen": {"status": "planned", "type": "sensor"},
            "future_android": {"status": "planned", "type": "ability"},
            "future_hardware": {"status": "planned", "type": "ability"}
        }
        
    def get_active_capabilities(self) -> list:
        return [k for k, v in self.capabilities.items() if v["status"] == "active"]
        
    def get_planned_capabilities(self) -> list:
        return [k for k, v in self.capabilities.items() if v["status"] == "planned"]
