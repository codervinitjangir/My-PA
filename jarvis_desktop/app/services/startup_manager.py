# jarvis_desktop/app/services/startup_manager.py

import os
import sys
from PySide6.QtCore import QObject

class StartupManager(QObject):
    """
    Windows Startup Shortcut Manager for 'Launch on Windows Startup' and 'Start Minimized'.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def get_startup_path(self) -> str:
        startup_folder = os.path.join(os.getenv("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
        return os.path.join(startup_folder, "JarvisDesktop.bat")

    def is_startup_enabled(self) -> bool:
        return os.path.exists(self.get_startup_path())

    def set_startup_enabled(self, enabled: bool):
        shortcut_path = self.get_startup_path()
        if enabled:
            try:
                python_exe = sys.executable.replace("python.exe", "pythonw.exe")
                main_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "app.py"))
                
                with open(shortcut_path, "w", encoding="utf-8") as f:
                    f.write(f'@echo off\nstart "" "{python_exe}" -m jarvis_desktop.app')
            except Exception as e:
                print(f"[StartupManager] Failed to set startup: {e}")
        else:
            if os.path.exists(shortcut_path):
                try:
                    os.remove(shortcut_path)
                except Exception as e:
                    print(f"[StartupManager] Failed to remove startup: {e}")
