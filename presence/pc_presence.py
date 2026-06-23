import ctypes
import os

class PCPresence:
    """
    Tracks hardware-level presence on the local PC (Windows).
    """
    def __init__(self):
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        self.last_input_info = LASTINPUTINFO()
        self.last_input_info.cbSize = ctypes.sizeof(self.last_input_info)

    def get_idle_time_seconds(self) -> float:
        """Returns the number of seconds the system has been idle (no mouse/kb input)."""
        try:
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(self.last_input_info)):
                millis = ctypes.windll.kernel32.GetTickCount() - self.last_input_info.dwTime
                return millis / 1000.0
        except Exception:
            pass
        return 0.0

    def is_locked(self) -> bool:
        """Checks if the workstation is locked."""
        # For V1, we provide a stub. A robust implementation requires WTSQuerySessionInformation.
        return False
