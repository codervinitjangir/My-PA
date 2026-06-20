from typing import Dict, Any, List, Optional
from datetime import datetime
from jarvis_os.session.session_models import WorkSession, SessionStatus
from jarvis_os.session.session_history import SessionHistory
from jarvis_os.session.session_tracker import SessionTracker
from jarvis_os.session.session_resumer import SessionResumer
from jarvis_os.session.session_summary import SessionSummary

class SessionManager:
    """
    Central coordinator for Work Session Intelligence.
    Tracks, resumes, and summarizes non-autonomous human working states.
    """
    def __init__(self):
        self.history = SessionHistory()
        self.tracker = SessionTracker(self.history)
        self.resumer = SessionResumer(self.tracker)
        self.summary_builder = SessionSummary()
        
    def generate_suggestions(self) -> List[str]:
        suggestions = []
        sessions = self.tracker.get_all_sessions()
        now = datetime.now()
        
        for s in sessions:
            if s.status == SessionStatus.PAUSED:
                # Rule: Long inactive session -> Suggest resuming
                if (now - s.updated_at).days >= 1:
                    suggestions.append(f"Project '{s.project}' has been paused for a while. Consider resuming it.")
            elif s.status == SessionStatus.ACTIVE:
                # Rule: Many pending tasks -> Suggest continuation
                if len(s.pending_items) >= 5:
                    suggestions.append(f"You have a lot of pending tasks in '{s.project}'. Keep going!")
                    
        return suggestions
