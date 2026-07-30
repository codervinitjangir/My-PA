# jarvis_desktop/app/services/app_state.py

from PySide6.QtCore import QObject, Signal

class AppState(QObject):
    """
    Central Reactive Application State for JARVIS Desktop.
    All UI widgets observe this state via Qt Signals instead of communicating directly with each other.
    """

    # Signals
    connection_status_changed = Signal(str)    # "online", "offline"
    voice_state_changed = Signal(str)          # "idle", "listening", "thinking", "speaking"
    execution_state_changed = Signal(str)      # "idle", "executing"
    current_mode_changed = Signal(str)          # "jarvis", "general", "realtime"
    chat_updated = Signal(list)                # List of chat message dicts
    activity_updated = Signal(list)            # List of timeline activity dicts
    setting_changed = Signal(str, bool)        # Key, Value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connection_status = "offline"
        self._voice_state = "idle"
        self._execution_state = "idle"
        self._current_mode = "jarvis"
        self._chat_messages = []
        self._activity_items = []
        self._settings = {
            "auto_activity": True,
            "auto_search": True,
            "thinking_sounds": True,
            "voice_interrupt": True
        }

    # Getters & Setters
    @property
    def connection_status(self) -> str:
        return self._connection_status

    def set_connection_status(self, status: str):
        if self._connection_status != status:
            self._connection_status = status
            self.connection_status_changed.emit(status)

    @property
    def voice_state(self) -> str:
        return self._voice_state

    def set_voice_state(self, state: str):
        if self._voice_state != state:
            self._voice_state = state
            self.voice_state_changed.emit(state)

    @property
    def execution_state(self) -> str:
        return self._execution_state

    def set_execution_state(self, state: str):
        if self._execution_state != state:
            self._execution_state = state
            self.execution_state_changed.emit(state)

    @property
    def current_mode(self) -> str:
        return self._current_mode

    def set_current_mode(self, mode: str):
        if self._current_mode != mode:
            self._current_mode = mode
            self.current_mode_changed.emit(mode)

    def add_chat_message(self, text: str, is_user: bool, sender_name: str = "Jarvis (Jarvis)", latency_info: str = ""):
        msg = {
            "text": text,
            "is_user": is_user,
            "sender_name": sender_name,
            "latency_info": latency_info
        }
        self._chat_messages.append(msg)
        self.chat_updated.emit(self._chat_messages)

    def add_activity_step(self, step_num: str, step_title: str, step_detail: str = ""):
        step = {"num": step_num, "title": step_title, "detail": step_detail}
        self._activity_items.append(step)
        self.activity_updated.emit(self._activity_items)

    def clear_activity(self):
        self._activity_items = []
        self.activity_updated.emit(self._activity_items)

    def set_setting(self, key: str, value: bool):
        self._settings[key] = value
        self.setting_changed.emit(key, value)

    def get_setting(self, key: str, default: bool = True) -> bool:
        return self._settings.get(key, default)
