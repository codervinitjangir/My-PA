# jarvis_desktop/app/services/recovery_manager.py

import asyncio
from PySide6.QtCore import QObject, Signal
from jarvis_desktop.app.services.event_bus import DesktopEventBus
from jarvis_desktop.app.services.system_state import SystemState

class RecoveryManager(QObject):
    """
    Self-healing Error Recovery Manager.
    Handles backend disconnects, network drops, and service timeouts with silent retries.
    Informs user via Toast Notifications: "Lost connection... → Reconnecting... → Connected".
    """
    recovery_status_changed = Signal(str) # "reconnecting", "recovered", "failed"

    def __init__(self, system_state: SystemState, event_bus: DesktopEventBus, backend_service, parent=None):
        super().__init__(parent)
        self.sys_state = system_state
        self.bus = event_bus
        self.backend = backend_service
        self.is_recovering = False

        self.bus.backend_disconnected.connect(self._handle_backend_disconnected)

    def _handle_backend_disconnected(self, reason: str):
        if self.is_recovering:
            return
        self.is_recovering = True
        self.sys_state.set_backend_status("reconnecting")
        self.bus.publish_notification("Backend Connection", "Lost connection... Attempting silent reconnect", "warning")
        
        asyncio.create_task(self._auto_reconnect_loop())

    async def _auto_reconnect_loop(self):
        max_attempts = 5
        attempt = 0
        while attempt < max_attempts and self.sys_state.backend_status != "online":
            attempt += 1
            await asyncio.sleep(2.0 * attempt) # Exponential backoff
            
            is_healthy = await self.backend.check_health()
            if is_healthy:
                self.sys_state.set_backend_status("online")
                self.bus.publish_notification("Backend Connection", "Connection restored successfully", "info")
                self.bus.publish_backend_connected()
                self.is_recovering = False
                return

        self.is_recovering = False
        self.bus.publish_notification("Backend Connection", "Unable to reconnect. Please check local server.", "error")
