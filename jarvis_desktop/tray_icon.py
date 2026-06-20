# jarvis_desktop/tray_icon.py

import os
import sys
from pathlib import Path
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
import urllib.request

API_URL = "http://127.0.0.1:8000"

class JarvisTrayIcon(QSystemTrayIcon):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        
        # Use a default icon from the system or a placeholder
        # Ideally, there should be an icon file in the app. For now, fallback.
        # Self drawing a simple icon could work, but QIcon() might be blank.
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
        else:
            # Fallback to standard app icon if available
            from PySide6.QtWidgets import QStyle
            self.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
            
        self.setToolTip("JARVIS Presence Mode")
        self.activated.connect(self.on_activated)
        
        self.menu = QMenu()
        
        # Actions
        open_action = QAction("Open Presence", self)
        open_action.triggered.connect(self.window.show)
        self.menu.addAction(open_action)
        
        dash_action = QAction("Open Dashboard", self)
        dash_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(f"{API_URL}/dashboard")))
        self.menu.addAction(dash_action)
        
        brief_action = QAction("Morning Brief", self)
        brief_action.triggered.connect(self.trigger_brief)
        self.menu.addAction(brief_action)
        
        resume_action = QAction("Resume Session", self)
        resume_action.triggered.connect(lambda: print("Resume Session not implemented"))
        self.menu.addAction(resume_action)
        
        self.menu.addSeparator()
        
        # Auto-start toggle
        self.startup_action = QAction("Launch JARVIS Presence at startup", self)
        self.startup_action.setCheckable(True)
        self.startup_action.setChecked(self.is_startup_enabled())
        self.startup_action.triggered.connect(self.toggle_startup)
        self.menu.addAction(self.startup_action)
        
        self.menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(quit_action)
        
        self.setContextMenu(self.menu)

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if self.window.isVisible():
                self.window.hide()
            else:
                self.window.show()

    def trigger_brief(self):
        try:
            urllib.request.urlopen(f"{API_URL}/briefing", timeout=5)
        except Exception as e:
            print("Failed to trigger brief:", e)

    def get_startup_path(self):
        startup_folder = os.path.join(os.getenv("APPDATA"), r"Microsoft\Windows\Start Menu\Programs\Startup")
        return os.path.join(startup_folder, "JarvisPresence.bat")

    def is_startup_enabled(self):
        return os.path.exists(self.get_startup_path())

    def toggle_startup(self, checked):
        shortcut_path = self.get_startup_path()
        if checked:
            try:
                # Get the path to pythonw.exe to run without a console window
                python_exe = sys.executable.replace("python.exe", "pythonw.exe")
                main_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
                
                # Write a simple batch file to the startup folder
                with open(shortcut_path, "w") as f:
                    f.write(f'@echo off\nstart "" "{python_exe}" "{main_script}"')
            except Exception as e:
                print("Failed to enable startup:", e)
        else:
            if os.path.exists(shortcut_path):
                try:
                    os.remove(shortcut_path)
                except Exception as e:
                    print("Failed to disable startup:", e)
