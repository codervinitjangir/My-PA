from typing import Dict, Any
from jarvis_os.workspaces.workspace_models import Workspace

class WorkspaceBuilder:
    """
    Constructs Workspace objects from available state.
    """
    def build(self, name: str, description: str, tools: list, global_state: Dict[str, Any]) -> Workspace:
        # In a real environment, this would filter sessions and pending_items relevant to this specific workspace.
        # For now, it aggregates current state based on simple heuristics.
        
        session_info = global_state.get("session", {})
        pending_count = session_info.get("pending", 0)
        
        digital_activity = global_state.get("digital_activity", {})
        activity_str = digital_activity.get("activity", "Unknown") if digital_activity else "Unknown"
        
        return Workspace(
            name=name,
            description=description,
            tools=tools,
            sessions=[session_info.get("active_session", "No active session")] if session_info else [],
            pending_items=pending_count,
            recent_activity=f"Detected {activity_str} activity"
        )
