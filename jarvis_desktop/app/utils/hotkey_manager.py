# jarvis_desktop/app/utils/hotkey_manager.py

import sys
import ctypes
from ctypes import wintypes
from PySide6.QtCore import QObject, Signal, QAbstractNativeEventFilter, QCoreApplication

# Windows API Constants
MOD_CONTROL = 0x0002
VK_SPACE = 0x20
WM_HOTKEY = 0x0312

class HotkeyNativeFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                self.callback()
                return True, 0
        return False, 0

class GlobalHotkeyManager(QObject):
    """
    Windows Native Global Hotkey Manager (captures Ctrl+Space system-wide).
    Uses ctypes RegisterHotKey API and QAbstractNativeEventFilter.
    """
    hotkey_pressed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user32 = ctypes.windll.user32
        self.hotkey_id = 9999
        self.is_registered = False

        self.native_filter = HotkeyNativeFilter(self._on_hotkey_triggered)

    def register_hotkey(self) -> bool:
        """Register Ctrl+Space global hotkey"""
        if sys.platform == 'win32':
            app = QCoreApplication.instance()
            if app:
                app.installNativeEventFilter(self.native_filter)

            # MOD_CONTROL = 0x0002, VK_SPACE = 0x20
            res = self.user32.RegisterHotKey(None, self.hotkey_id, MOD_CONTROL, VK_SPACE)
            self.is_registered = bool(res)
            return self.is_registered
        return False

    def unregister_hotkey(self):
        if sys.platform == 'win32' and self.is_registered:
            self.user32.UnregisterHotKey(None, self.hotkey_id)
            self.is_registered = False

    def _on_hotkey_triggered(self):
        self.hotkey_pressed.emit()
