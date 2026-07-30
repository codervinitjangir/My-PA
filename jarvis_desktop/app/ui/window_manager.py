# jarvis_desktop/app/ui/window_manager.py

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from jarvis_desktop.app.ui.main_window import MainWindow
from jarvis_desktop.app.ui.overlay_manager import OverlayManager
from jarvis_desktop.app.ui.command_palette import CommandPalette
from jarvis_desktop.app.ui.tray_manager import TrayManager
from jarvis_desktop.app.utils.hotkey_manager import GlobalHotkeyManager
from jarvis_desktop.app.utils.settings_manager import SettingsManager

class WindowManager(QObject):
    """
    Unified Window Lifecycle & Overlay Manager for JARVIS Desktop.
    Controls MainWindow, TrayManager, OverlayManager (HUD), CommandPalette,
    and Global Hotkey (Ctrl+Space) registration.
    """
    def __init__(self, backend_service, parent=None):
        super().__init__(parent)
        self.backend = backend_service
        self.settings_mgr = SettingsManager()

        # Instantiate Primary Windows & Overlays
        self.main_win = MainWindow()
        self.overlay_mgr = OverlayManager()
        self.cmd_palette = CommandPalette()
        self.tray = TrayManager()
        self.hotkey_mgr = GlobalHotkeyManager(self)

        self._restore_saved_state()
        self._wire_connections()

    def _restore_saved_state(self):
        pos, size, sidebar_open, mode = self.settings_mgr.load_window_geometry()
        if pos:
            self.main_win.move(pos)
        self.main_win.resize(size)
        if sidebar_open:
            self.main_win.sidebar.show()
        self.main_win.header.set_active_mode(mode)

    def _wire_connections(self):
        # Tray connections
        self.tray.open_requested.connect(self.show_main_window)
        self.tray.quick_chat_requested.connect(self.cmd_palette.show_palette)
        self.tray.settings_requested.connect(self.main_win.show_settings)
        self.tray.exit_requested.connect(self.exit_application)

        # Command palette execution -> forward command to main window
        self.cmd_palette.command_executed.connect(self._on_palette_command)

        # Global Hotkey Ctrl+Space -> Show Command Palette
        self.hotkey_mgr.hotkey_pressed.connect(self.cmd_palette.show_palette)
        self.hotkey_mgr.register_hotkey()

    def _on_palette_command(self, cmd_name: str):
        if cmd_name == "Open Settings":
            self.main_win.show_settings()
        else:
            self.show_main_window()
            self.main_win.input_bar.send_requested.emit(cmd_name)

    def show_main_window(self):
        self.main_win.show()
        self.main_win.raise_()
        self.main_win.activateWindow()

    def exit_application(self):
        # Save geometry before exit
        self.settings_mgr.save_window_geometry(
            self.main_win.pos(),
            self.main_win.size(),
            self.main_win.sidebar.isVisible(),
            self.main_win.header._active_mode
        )
        self.hotkey_mgr.unregister_hotkey()
        QApplication.instance().quit()
