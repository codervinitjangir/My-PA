import logging
from core.buses.bus_manager import bus_manager

logger = logging.getLogger("J.A.R.V.I.S")

class AudioManager:
    """
    Manages raw audio input/output and publishes chunks to the VoiceBus.
    """
    def __init__(self):
        self.is_listening = False

    def start_listening(self):
        self.is_listening = True
        logger.info("[AudioManager] Started pushing audio to VoiceBus.")
        # Future: Run PyAudio loop and call bus_manager.voice_bus.publish(chunk)

    def stop_listening(self):
        self.is_listening = False
