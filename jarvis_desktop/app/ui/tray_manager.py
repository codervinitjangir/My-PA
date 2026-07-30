# jarvis_desktop/app/ui/tray_manager.py

import sys
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtCore import Qt, Signal

class TrayManager(QSystemTrayIcon):
    """
    Windows System Tray Integration with dynamic status icon badges
    (Gray=Offline, Purple=Idle, Blue=Listening, Green=Executing)
    and rich Context Menu.
    """
    open_requested = Signal()
    quick_chat_requested = Signal()
    settings_requested = Signal()
    restart_services_requested = Signal()
    reconnect_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setToolTip("JARVIS — Ready")

        # Initial Badge Icon (Purple=Idle)
        self.update_tray_badge("purple")

        # Setup Context Menu
        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #0c0c20;
                border: 1px solid rgba(124, 106, 239, 0.3);
                border-radius: 10px;
                padding: 6px;
                color: #ffffff;
                font-family: 'Segoe UI Variable', sans-serif;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 6px;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #7c6aef;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.1);
                margin: 4px 8px;
            }
        """)

        # Menu Actions
        self.open_action = QAction("💻 Open Dashboard", self)
        self.open_action.triggered.connect(self.open_requested.emit)
        self.menu.addAction(self.open_action)

        self.chat_action = QAction("💬 Quick Chat", self)
        self.chat_action.triggered.connect(self.quick_chat_requested.emit)
        self.menu.addAction(self.chat_action)

        self.menu.addSeparator()

        self.reconnect_action = QAction("🔄 Reconnect Backend", self)
        self.reconnect_action.triggered.connect(self.reconnect_requested.emit)
        self.menu.addAction(self.reconnect_action)

        self.restart_action = QAction("⚡ Restart Services", self)
        self.restart_action.triggered.connect(self.restart_services_requested.emit)
        self.menu.addAction(self.restart_action)

        self.settings_action = QAction("⚙️ Settings", self)
        self.settings_action.triggered.connect(self.settings_requested.emit)
        self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        self.exit_action = QAction("🚪 Exit JARVIS", self)
        self.exit_action.triggered.connect(self.exit_requested.emit)
        self.menu.addAction(self.exit_action)

        self.setContextMenu(self.menu)
        self.activated.connect(self._on_activated)
        self.show()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger or reason == QSystemTrayIcon.DoubleClick:
            self.open_requested.emit()

    def update_tray_badge(self, color_name: str):
        """
        Dynamically paint 24x24 tray icon badge:
        - "gray": Offline
        - "purple": Idle / Online
        - "blue": Listening
        - "green": Executing
        """
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        color_map = {
            "gray": QColor(140, 140, 160),
            "purple": QColor(124, 106, 239),
            "blue": QColor(78, 205, 196),
            "green": QColor(81, 207, 102)
        }
        fill_color = color_map.get(color_name.lower(), QColor(124, 106, 239))

        # Outer ring
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(10, 10, 28, 220))
        painter.drawEllipse(2, 2, 20, 20)

        # Inner badge circle
        painter.setBrush(fill_color)
        painter.drawEllipse(5, 5, 14, 14)

        # Letter 'J' in center
        painter.setPen(QColor(255, 255, 255))
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(10)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "J")

        painter.end()

        self.setIcon(QIcon(pixmap))

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    tray = TrayManager()
    sys.exit(app.exec())
