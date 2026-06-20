from typing import Dict, Any
import logging

logger = logging.getLogger("J.A.R.V.I.S")

class AwarenessMonitor:
    """
    Observes changes in projects, goals, memory, and priorities.
    Purely observational, executes nothing.
    """
    def __init__(self):
        self.last_state = {}
        
    def observe_changes(self, current_state: Dict[str, Any]):
        """
        Compares the new state against the previous state to log changes.
        """
        if not self.last_state:
            self.last_state = current_state
            return
            
        # Check Project changes
        if len(current_state.get("active_projects", [])) != len(self.last_state.get("active_projects", [])):
            logger.info("[AWARENESS] Monitored change in active projects.")
            
        # Check Goal changes
        if len(current_state.get("active_goals", [])) != len(self.last_state.get("active_goals", [])):
            logger.info("[AWARENESS] Monitored change in active goals.")
            
        # Check Priority/Urgent changes
        if len(current_state.get("urgent_items", [])) != len(self.last_state.get("urgent_items", [])):
            logger.info("[AWARENESS] Monitored change in urgent items priority.")
            
        self.last_state = current_state
