from jarvis_os.session.session_models import WorkSession

class SessionSummary:
    def build_session_summary(self, session: WorkSession) -> str:
        if not session:
            return "No active session."
            
        summary = f"Current session:\nProject: {session.project}\nFocus: {session.focus}\n\nPending:\n"
        if session.pending_items:
            for item in session.pending_items:
                summary += f"* {item}\n"
        else:
            summary += "* None\n"
            
        summary += "\nCompleted:\n"
        if session.completed_items:
            for item in session.completed_items:
                summary += f"* {item}\n"
        else:
            summary += "* None\n"
            
        return summary
