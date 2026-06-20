# jarvis_desktop/main.py

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication

from jarvis_desktop.presence_window import PresenceWindow
from jarvis_desktop.tray_icon import JarvisTrayIcon

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Initialize the Presence Window
    window = PresenceWindow()
    
    # Position window at the bottom right of the primary screen
    screen = QGuiApplication.primaryScreen().availableGeometry()
    
    window_width = window.width()
    window_height = window.height()
    
    # Add a small margin from the edge
    margin = 20
    x = screen.width() - window_width - margin
    y = screen.height() - window_height - margin
    
    window.move(x, y)
    
    # Initialize the System Tray Icon
    tray = JarvisTrayIcon(window)
    tray.show()
    
    # Don't show the window by default on startup unless requested
    # The user can toggle it from the tray
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
