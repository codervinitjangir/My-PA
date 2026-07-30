# jarvis_desktop/app/services/desktop_state.py

from PySide6.QtCore import QObject, Signal

class DesktopState(QObject):
    """
    Manages Desktop UI presentation state (Window layout, Sidebar, Overlays, Tray, Preferences).
    Separated cleanly from SystemState.
    """
    current_mode_changed = Signal(str)          # "jarvis", "general", "realtime"
    sidebar_toggled = Signal(bool)             # True=Open, False=Closed
    theme_changed = Signal(str)                # "dark", "light", "auto"
    setting_changed = Signal(str, bool)        # Key, Value
    hud_state_changed = Signal(str, str)       # hud_mode ("listening", "thinking", "executing", "done"), text

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_mode = "jarvis"
        self._sidebar_open = False
        self._theme = "dark"
        self._hud_mode = "hidden"
        self._hud_text = ""
        self._settings = {
            "launch_at_startup": False,
            "start_minimized": False,
            "hotkey": "Ctrl+Space",
            "hud_opacity": 0.95,
            "notification_sounds": True,
            "auto_activity": True,
            "auto_search": True,
            "thinking_sounds": True,
            "voice_interrupt": True
        }

    @property
    def current_mode(self) -> str:
        return self._current_mode

    def set_current_mode(self, mode: str):
        if self._current_mode != mode:
            self._current_mode = mode
            self.current_mode_changed.emit(mode)

    @property
    def sidebar_open(self) -> bool:
        return self._sidebar_open

    def set_sidebar_open(self, open_state: bool):
        if self._sidebar_open != open_state:
            self._sidebar_open = open_state
            self.sidebar_toggled.emit(open_state)

    @property
    def theme(self) -> str:
        return self._theme

    def set_theme(self, theme_name: str):
        if self._theme != theme_name:
            self._theme = theme_name
            self.theme_changed.emit(theme_name)

    def set_hud_state(self, mode: str, text: str = ""):
        self._hud_mode = mode
        self._hud_text = text
        self.hud_state_changed.emit(mode, text)

    def set_setting(self, key: str, value: bool):
        self._settings[key] = value
        self.setting_changed.emit(key, value)

    def get_setting(self, key: str, default=None):
        return self._settings.get(key, default)
