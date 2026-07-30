# jarvis_desktop/app/services/desktop_service_layer.py

from PySide6.QtCore import QObject
from jarvis_desktop.app.services.event_bus import DesktopEventBus
from jarvis_desktop.app.services.system_state import SystemState
from jarvis_desktop.app.services.desktop_state import DesktopState
from jarvis_desktop.app.services.recovery_manager import RecoveryManager

class DesktopServiceLayer(QObject):
    """
    Operating System Abstraction & Service Layer for Windows integration.
    Wraps Tray, Overlays, Notifications, Window Focus, Global Hotkeys, and Startup.
    """
    def __init__(self, backend_service, parent=None):
        super().__init__(parent)
        self.bus = DesktopEventBus(self)
        self.system_state = SystemState(self)
        self.desktop_state = DesktopState(self)
        self.backend = backend_service
        self.recovery_mgr = RecoveryManager(self.system_state, self.bus, self.backend, self)

        # Wire backend status to SystemState
        self.backend.status_changed.connect(
            lambda online: self.system_state.set_backend_status("online" if online else "offline")
        )
