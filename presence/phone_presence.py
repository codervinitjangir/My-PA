class PhonePresence:
    """
    Tracks whether the user's phone is connected/active via the Android bridge.
    """
    def __init__(self):
        self.is_connected = False

    def check_connection_status(self) -> bool:
        # Stub for V1
        return self.is_connected

    def set_connection_status(self, status: bool):
        self.is_connected = status
