from jarvis_os.core.state_manager import GlobalStateManager
from jarvis_os.dashboard.dashboard_builder import DashboardBuilder

class DashboardManager:
    def __init__(self):
        self.builder = DashboardBuilder()
        self._state_mgr = GlobalStateManager()

    def get_dashboard(self) -> dict:
        """
        Retrieves the deterministic, sub-100ms dashboard state.
        Zero LLM calls.
        """
        global_state = self._state_mgr.build_global_state()
        state = self.builder.build_state(global_state)
        return state.model_dump()

