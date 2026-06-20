from typing import Dict, Optional
from datetime import datetime
from jarvis_os.session.session_models import WorkSession, SessionStatus
from jarvis_os.session.session_history import SessionHistory

class SessionTracker:
    def __init__(self, history: SessionHistory):
        self.sessions: Dict[str, WorkSession] = {}
        self.active_session_id: Optional[str] = None
        self.history = history
        
    def start_session(self, title: str, domain: str, project: str, focus: str, priority: int = 1) -> WorkSession:
        if self.active_session_id:
            self.pause_session(self.active_session_id)
            
        session = WorkSession(title=title, domain=domain, project=project, focus=focus, priority=priority)
        self.sessions[session.id] = session
        self.active_session_id = session.id
        
        self.history.record_change("START_SESSION", project, focus, {"status": "ACTIVE"})
        return session
        
    def update_session(self, session_id: str, pending: list = None, completed: list = None, notes: str = None) -> WorkSession:
        if session_id not in self.sessions:
            raise ValueError("Session not found")
            
        session = self.sessions[session_id]
        changes = {}
        
        if pending is not None:
            session.pending_items = pending
            changes["pending_items"] = pending
        if completed is not None:
            session.completed_items = completed
            changes["completed_items"] = completed
        if notes is not None:
            session.notes = notes
            changes["notes"] = notes
            
        session.updated_at = datetime.now()
        self.history.record_change("UPDATE_SESSION", session.project, session.focus, changes)
        return session
        
    def pause_session(self, session_id: str) -> WorkSession:
        if session_id in self.sessions:
            self.sessions[session_id].status = SessionStatus.PAUSED
            self.sessions[session_id].updated_at = datetime.now()
            if self.active_session_id == session_id:
                self.active_session_id = None
            self.history.record_change("PAUSE_SESSION", self.sessions[session_id].project, self.sessions[session_id].focus, {"status": "PAUSED"})
            return self.sessions[session_id]
        return None

    def resume_session(self, session_id: str) -> WorkSession:
        if session_id in self.sessions:
            if self.active_session_id and self.active_session_id != session_id:
                self.pause_session(self.active_session_id)
                
            self.sessions[session_id].status = SessionStatus.ACTIVE
            self.sessions[session_id].updated_at = datetime.now()
            self.active_session_id = session_id
            self.history.record_change("RESUME_SESSION", self.sessions[session_id].project, self.sessions[session_id].focus, {"status": "ACTIVE"})
            return self.sessions[session_id]
        return None
        
    def complete_session(self, session_id: str) -> WorkSession:
        if session_id in self.sessions:
            self.sessions[session_id].status = SessionStatus.COMPLETED
            self.sessions[session_id].updated_at = datetime.now()
            if self.active_session_id == session_id:
                self.active_session_id = None
            self.history.record_change("COMPLETE_SESSION", self.sessions[session_id].project, self.sessions[session_id].focus, {"status": "COMPLETED"})
            return self.sessions[session_id]
        return None
        
    def get_all_sessions(self) -> list:
        return list(self.sessions.values())
