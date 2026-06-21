import logging
import threading
import time

logger = logging.getLogger("J.A.R.V.I.S")

class VoiceService:
    """
    Offline Voice pipeline. 
    Adopts the ISAIR pattern: Local STT (e.g., Whisper) with echo cancellation 
    to ignore its own TTS, preventing feedback loops.
    """
    def __init__(self):
        self.is_speaking = False
        self._listening = False
        self._listen_thread = None

    def start_listening(self, callback):
        """Starts the continuous offline listening loop."""
        self._listening = True
        self._listen_thread = threading.Thread(target=self._listen_loop, args=(callback,), daemon=True)
        self._listen_thread.start()
        logger.info("[VOICE] Offline listening pipeline started.")

    def _listen_loop(self, callback):
        """Simulated offline Whisper listening loop."""
        while self._listening:
            time.sleep(1)
            # In a full implementation, audio bytes would be fed to Whisper here.
            # If self.is_speaking is True, the transcribed text is discarded.

    def stop_listening(self):
        self._listening = False

    def notify_speaking_start(self):
        """Sets flag to ignore STT input (Echo Cancellation)"""
        self.is_speaking = True
        logger.debug("[VOICE] Echo cancellation: ON (Ignoring microphone)")

    def notify_speaking_end(self):
        """Clears flag to resume STT input"""
        self.is_speaking = False
        logger.debug("[VOICE] Echo cancellation: OFF (Listening to microphone)")
