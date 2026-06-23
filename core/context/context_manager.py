from presence.pc_presence import PCPresence
from presence.phone_presence import PhonePresence
from presence.meeting_presence import MeetingPresence

class ContextManager:
    """
    Aggregates data from the Presence Engine to build the current OS context.
    Provides this context to the Orchestrator/Decision Engine.
    """
    def __init__(self):
        self.pc_presence = PCPresence()
        self.phone_presence = PhonePresence()
        self.meeting_presence = MeetingPresence()

    def get_current_context(self) -> str:
        """
        Returns a formatted string representing the current user and device context.
        """
        idle_time = self.pc_presence.get_idle_time_seconds()
        is_locked = self.pc_presence.is_locked()
        phone_conn = self.phone_presence.check_connection_status()
        meeting_active = self.meeting_presence.check_meeting_status()

        context_parts = []
        if is_locked:
            context_parts.append("PC: Locked")
        if meeting_active:
            context_parts.append("Meeting: Active")
        if idle_time > 300: # 5 minutes
            context_parts.append(f"User Status: Away (Idle for {int(idle_time)}s)")
        if phone_conn:
            context_parts.append("Phone: Connected")

        if not context_parts:
            return "Status: Normal / Active"
        
        return " | ".join(context_parts)
