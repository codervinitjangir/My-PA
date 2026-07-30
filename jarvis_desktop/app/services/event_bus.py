# jarvis_desktop/app/services/event_bus.py

from PySide6.QtCore import QObject, Signal

class DesktopEventBus(QObject):
    """
    Central Event Bus for loose-coupling across JARVIS Desktop modules.
    Components publish and subscribe to desktop events without tight coupling.
    """

    # Event Signals
    voice_started = Signal(str)          # voice_mode
    voice_stopped = Signal()
    voice_state_changed = Signal(str)    # granular voice state

    backend_connected = Signal()
    backend_disconnected = Signal(str)  # reason

    chat_started = Signal(str)           # prompt
    chat_finished = Signal(dict)         # response_payload

    notification_created = Signal(dict) # {title, message, type}

    window_opened = Signal(str)          # window_name
    window_closed = Signal(str)          # window_name

    desktop_action_executed = Signal(str, dict) # action_name, payload
    error_occurred = Signal(str, str)   # component, error_message

    def __init__(self, parent=None):
        super().__init__(parent)

    def publish_voice_started(self, mode: str = "voice"):
        self.voice_started.emit(mode)

    def publish_voice_stopped(self):
        self.voice_stopped.emit()

    def publish_voice_state(self, state: str):
        self.voice_state_changed.emit(state)

    def publish_backend_connected(self):
        self.backend_connected.emit()

    def publish_backend_disconnected(self, reason: str = "Connection lost"):
        self.backend_disconnected.emit(reason)

    def publish_chat_started(self, prompt: str):
        self.chat_started.emit(prompt)

    def publish_chat_finished(self, response: dict):
        self.chat_finished.emit(response)

    def publish_notification(self, title: str, message: str, type_: str = "info"):
        self.notification_created.emit({"title": title, "message": message, "type": type_})

    def publish_window_opened(self, window_name: str):
        self.window_opened.emit(window_name)

    def publish_window_closed(self, window_name: str):
        self.window_closed.emit(window_name)

    def publish_action(self, action_name: str, payload: dict = None):
        self.desktop_action_executed.emit(action_name, payload or {})

    def publish_error(self, component: str, error_msg: str):
        self.error_occurred.emit(component, error_msg)
