class MeetingPresence:
    """
    Tracks whether the user is currently in a meeting.
    """
    def __init__(self):
        self.is_active = False

    def check_meeting_status(self) -> bool:
        # Stub for V1: Hook into calendar API or active Zoom/Teams process
        return self.is_active

    def set_meeting_status(self, status: bool):
        self.is_active = status
