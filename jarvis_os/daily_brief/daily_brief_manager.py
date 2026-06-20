from jarvis_os.core.global_state import build_global_state
from jarvis_os.daily_brief.daily_brief_builder import DailyBriefBuilder

class DailyBriefManager:
    def __init__(self):
        self.builder = DailyBriefBuilder()
        
    def get_briefing(self) -> dict:
        """
        Retrieves the deterministic, sub-50ms briefing state.
        Zero LLM calls.
        """
        global_state = build_global_state()
        state = self.builder.build_state(global_state)
        return state.model_dump()
