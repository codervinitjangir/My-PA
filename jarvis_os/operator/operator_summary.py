from typing import Dict, Any

class OperatorSummary:
    """
    Builds the final combined output state for the user interface.
    """
    def build_operator_summary(self, global_state: Dict[str, Any]) -> str:
        awareness = global_state.get("awareness", {})
        session = global_state.get("session", {})
        recommendation = global_state.get("recommendation", [])
        computer = global_state.get("computer", {})
        
        focus = session.get("focus", awareness.get("current_focus", "None"))
        project = session.get("project", awareness.get("active_projects", ["None"])[0] if awareness.get("active_projects") else "None")
        pending = session.get("pending_items", [])
        
        rec_str = "\n".join([f"* {r.get('title', '')}: {r.get('reason', '')}" for r in recommendation]) if recommendation else "* None"
        pending_str = "\n".join([f"* {p}" for p in pending]) if pending else "* None"
        
        return f"""[OPERATOR SUMMARY]
Current focus: {focus}
Current project: {project}

Pending items:
{pending_str}

Recommendations:
{rec_str}

Desktop state:
{computer.get("summary", "Unknown")}
"""
