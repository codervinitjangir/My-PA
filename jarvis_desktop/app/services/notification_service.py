# jarvis_desktop/app/services/notification_service.py

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QSystemTrayIcon

class NotificationService(QObject):
    """
    Multi-Tier Notification System:
    1. Windows Native Toast (via QSystemTrayIcon)
    2. Fallback In-App Toast
    3. Persistent Notification History Log
    """
    notification_logged = Signal(dict) # {timestamp, title, message, type}

    def __init__(self, tray_icon: QSystemTrayIcon = None, parent=None):
        super().__init__(parent)
        self.tray = tray_icon
        self.history = []

    def notify(self, title: str, message: str, type_: str = "info"):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        notif_item = {
            "timestamp": timestamp,
            "title": title,
            "message": message,
            "type": type_
        }
        self.history.append(notif_item)
        self.notification_logged.emit(notif_item)

        # Dispatch Windows Native Toast if tray icon is available
        if self.tray and self.tray.isVisible():
            icon_type = QSystemTrayIcon.Information
            if type_ == "warning":
                icon_type = QSystemTrayIcon.Warning
            elif type_ == "error":
                icon_type = QSystemTrayIcon.Critical

            self.tray.showMessage(title, message, icon_type, 3000)
