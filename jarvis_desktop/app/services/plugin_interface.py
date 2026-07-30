# jarvis_desktop/app/services/plugin_interface.py

from PySide6.QtCore import QObject
from jarvis_desktop.app.services.event_bus import DesktopEventBus

class DesktopPlugin(QObject):
    """
    Base Plugin Interface for future desktop extension modules.
    Plugins subscribe to DesktopEventBus events without altering core UI code.
    """
    def __init__(self, name: str, event_bus: DesktopEventBus, parent=None):
        super().__init__(parent)
        self.name = name
        self.bus = event_bus

    def on_event(self, event_type: str, data: dict):
        """Override in subclass to handle events"""
        pass

class PluginManager(QObject):
    """
    Plugin Registry & Lifecycle Manager.
    """
    def __init__(self, event_bus: DesktopEventBus, parent=None):
        super().__init__(parent)
        self.bus = event_bus
        self.plugins = {}

    def register_plugin(self, plugin: DesktopPlugin):
        self.plugins[plugin.name] = plugin
        print(f"[PluginManager] Registered plugin: {plugin.name}")

    def unregister_plugin(self, name: str):
        if name in self.plugins:
            del self.plugins[name]

    def broadcast_event(self, event_type: str, data: dict = None):
        payload = data or {}
        for plugin in self.plugins.values():
            try:
                plugin.on_event(event_type, payload)
            except Exception as e:
                print(f"[PluginManager] Plugin '{plugin.name}' error on event {event_type}: {e}")
