import time
from typing import Dict, Any, Tuple
from jarvis_os.workspaces.workspace_models import Workspace
from jarvis_os.workspaces.workspace_builder import WorkspaceBuilder

class WorkspaceManager:
    """
    Manages defined Workspaces and infers the Suggested Workspace based on Digital Activity and State.
    """
    def __init__(self):
        self.builder = WorkspaceBuilder()
        # Hardcoded contexts for demonstration
        self.defined_workspaces = [
            {"name": "Jarvis", "desc": "Building the J.A.R.V.I.S OS", "tools": ["VS Code", "GitHub", "Terminal"]},
            {"name": "Vision", "desc": "Long-term planning and architecture", "tools": ["Notion", "Excalidraw", "Browser"]},
            {"name": "Career", "desc": "Job applications and networking", "tools": ["LinkedIn", "Resume.pdf", "Gmail"]},
            {"name": "General", "desc": "Everyday tasks and administration", "tools": ["Browser", "Spotify", "Notes"]}
        ]

    def infer_workspace(self, global_state: Dict[str, Any]) -> Tuple[Workspace, Workspace]:
        """
        Returns (Current Workspace, Suggested Workspace)
        Executes in < 50ms without LLM overhead.
        """
        start_time = time.time()
        
        # In a real scenario, the current workspace is set by the user or session.
        # Here we mock it based on active session for demonstration.
        session_info = global_state.get("session", {})
        active_session = session_info.get("active_session", "")
        
        digital_activity = global_state.get("digital_activity", {})
        activity_type = digital_activity.get("activity", "")
        
        # Deterministic inference logic
        suggested_name = "General"
        if activity_type == "Building" or "Jarvis" in active_session:
            suggested_name = "Jarvis"
        elif activity_type == "Job Search":
            suggested_name = "Career"
        elif activity_type == "Research" or "Vision" in active_session:
            suggested_name = "Vision"
            
        # Build the workspace objects
        suggested_data = next((w for w in self.defined_workspaces if w["name"] == suggested_name), self.defined_workspaces[3])
        current_data = next((w for w in self.defined_workspaces if w["name"] == "Jarvis"), self.defined_workspaces[0]) # Mock active as Jarvis
        
        suggested_ws = self.builder.build(suggested_data["name"], suggested_data["desc"], suggested_data["tools"], global_state)
        current_ws = self.builder.build(current_data["name"], current_data["desc"], current_data["tools"], global_state)
        
        # Enforce performance rule
        if (time.time() - start_time) * 1000 > 50:
            pass # Handle performance warning
            
        return current_ws, suggested_ws
