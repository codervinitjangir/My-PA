from jarvis_os.core.state_manager import GlobalStateManager
from jarvis_os.daily_brief.daily_brief_builder import DailyBriefBuilder

class DailyBriefManager:
    def __init__(self):
        self.builder = DailyBriefBuilder()
        self._state_mgr = GlobalStateManager()

    def get_briefing(self) -> dict:
        """
        Retrieves the deterministic, sub-50ms briefing state.
        Zero LLM calls.
        """
        global_state = self._state_mgr.build_global_state()
        state = self.builder.build_state(global_state)
        
        try:
            from app.scheduler import LAST_BRIEFING
            if LAST_BRIEFING and LAST_BRIEFING != "No briefing yet.":
                state.today_focus = LAST_BRIEFING
        except ImportError:
            pass
            
        return state.model_dump()
