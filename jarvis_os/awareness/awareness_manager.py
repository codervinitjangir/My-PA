from typing import Dict, Any
from jarvis_os.awareness.awareness_builder import AwarenessBuilder
from jarvis_os.awareness.awareness_suggester import AwarenessSuggester
from jarvis_os.awareness.awareness_monitor import AwarenessMonitor

class AwarenessManager:
    """
    Coordinates the Self Awareness Layer.
    Brings together the Monitor, Suggester, and Builder.
    """
    def __init__(self):
        self.builder = AwarenessBuilder()
        self.suggester = AwarenessSuggester()
        self.monitor = AwarenessMonitor()
        
    def build_awareness_state(self, raw_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the awareness pipeline to generate the final awareness state.
        """
        # 1. Generate Rules-Based Suggestions
        suggestions = self.suggester.generate_suggestions(raw_inputs)
        
        # 2. Build the final structured state
        awareness_state = self.builder.build_awareness_state(
            boss_state=raw_inputs.get("boss_state", {}),
            active_projects=raw_inputs.get("active_projects", []),
            active_goals=raw_inputs.get("active_goals", []),
            urgent_items=raw_inputs.get("urgent_items", []),
            pending_items=raw_inputs.get("pending_items", []),
            suggestions=suggestions
        )
        
        # 3. Monitor for any structural changes
        self.monitor.observe_changes(awareness_state)
        
        return awareness_state
