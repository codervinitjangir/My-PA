# jarvis_desktop/app/services/system_state.py

from PySide6.QtCore import QObject, Signal

class SystemState(QObject):
    """
    Manages system & backend service states separately from UI layout state.
    Tracks Backend, Internet, Telegram Bridge, Voice Pipeline, and Memory DB statuses.
    """
    backend_status_changed = Signal(str)    # "online", "offline", "reconnecting"
    internet_status_changed = Signal(bool)   # True, False
    telegram_status_changed = Signal(bool)   # True, False
    voice_state_changed = Signal(str)        # "sleeping", "wake_word", "listening", "recording", "uploading", "routing", "thinking", "streaming", "speaking", "interrupted", "completed", "idle"
    memory_db_status_changed = Signal(bool)  # True, False

    def __init__(self, parent=None):
        super().__init__(parent)
        self._backend_status = "offline"
        self._internet_status = True
        self._telegram_status = False
        self._voice_state = "idle"
        self._memory_db_status = True

    @property
    def backend_status(self) -> str:
        return self._backend_status

    def set_backend_status(self, status: str):
        if self._backend_status != status:
            self._backend_status = status
            self.backend_status_changed.emit(status)

    @property
    def internet_status(self) -> bool:
        return self._internet_status

    def set_internet_status(self, status: bool):
        if self._internet_status != status:
            self._internet_status = status
            self.internet_status_changed.emit(status)

    @property
    def telegram_status(self) -> bool:
        return self._telegram_status

    def set_telegram_status(self, status: bool):
        if self._telegram_status != status:
            self._telegram_status = status
            self.telegram_status_changed.emit(status)

    @property
    def voice_state(self) -> str:
        return self._voice_state

    def set_voice_state(self, state: str):
        if self._voice_state != state:
            self._voice_state = state
            self.voice_state_changed.emit(state)

    @property
    def memory_db_status(self) -> bool:
        return self._memory_db_status

    def set_memory_db_status(self, status: bool):
        if self._memory_db_status != status:
            self._memory_db_status = status
            self.memory_db_status_changed.emit(status)
