from jarvis_os.core.global_state import build_global_state
from jarvis_os.dashboard.dashboard_builder import DashboardBuilder

class DashboardManager:
    def __init__(self):
        self.builder = DashboardBuilder()
        
    def get_dashboard(self) -> dict:
        """
        Retrieves the deterministic, sub-100ms dashboard state.
        Zero LLM calls.
        """
        global_state = build_global_state()
        state = self.builder.build_state(global_state)
        return state.model_dump()
