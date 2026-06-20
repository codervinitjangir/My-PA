from datetime import datetime, date
from jarvis_os.session.session_models import WorkSession, SessionStatus
from jarvis_os.session.session_tracker import SessionTracker

class SessionResumer:
    """
    Deterministic rule-based engine to find the correct session to resume.
    NO AI is used.
    """
    def __init__(self, tracker: SessionTracker):
        self.tracker = tracker
        
    def resume_previous_session(self, context_clue: str = "latest", active_project: str = None) -> WorkSession:
        sessions = self.tracker.get_all_sessions()
        if not sessions:
            return None
            
        # Filter out completed sessions
        valid_sessions = [s for s in sessions if s.status != SessionStatus.COMPLETED]
        if not valid_sessions:
            return None
            
        today = date.today()
        
        # Rule: active project -> highest priority session for that project
        if active_project:
            proj_sessions = [s for s in valid_sessions if s.project.lower() == active_project.lower()]
            if proj_sessions:
                best_session = sorted(proj_sessions, key=lambda x: (x.priority, x.updated_at), reverse=True)[0]
                return self.tracker.resume_session(best_session.id)
                
        # Rule: today -> same day session
        if context_clue.lower() == "today":
            today_sessions = [s for s in valid_sessions if s.updated_at.date() == today]
            if today_sessions:
                best_session = sorted(today_sessions, key=lambda x: x.updated_at, reverse=True)[0]
                return self.tracker.resume_session(best_session.id)
                
        # Rule: yesterday / latest -> latest session overall
        best_session = sorted(valid_sessions, key=lambda x: x.updated_at, reverse=True)[0]
        return self.tracker.resume_session(best_session.id)
