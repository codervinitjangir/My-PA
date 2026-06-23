from core.buses.base_bus import EventBus

class BusManager:
    """
    Central coordinator for all domain-specific event buses in the OS.
    """
    def __init__(self):
        self.voice_bus = EventBus("VoiceBus")
        self.automation_bus = EventBus("AutomationBus")
        self.notification_bus = EventBus("NotificationBus")

# Global singleton
bus_manager = BusManager()
