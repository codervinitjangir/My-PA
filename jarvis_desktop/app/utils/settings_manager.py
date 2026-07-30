# jarvis_desktop/app/utils/settings_manager.py

from PySide6.QtCore import QSettings, QPoint, QSize

class SettingsManager:
    """
    QSettings Persistent Storage Manager.
    Remembers window position, size, sidebar state, active mode, and theme settings across restarts.
    """
    def __init__(self):
        self.settings = QSettings("JarvisAI", "JarvisDesktop")

    def save_window_geometry(self, pos: QPoint, size: QSize, sidebar_open: bool, mode: str):
        self.settings.setValue("window/pos", pos)
        self.settings.setValue("window/size", size)
        self.settings.setValue("window/sidebar_open", sidebar_open)
        self.settings.setValue("window/mode", mode)

    def load_window_geometry(self, default_size=QSize(1280, 800)):
        pos = self.settings.value("window/pos", None)
        size = self.settings.value("window/size", default_size)
        sidebar_open = self.settings.value("window/sidebar_open", False, type=bool)
        mode = self.settings.value("window/mode", "jarvis")
        return pos, size, sidebar_open, mode
