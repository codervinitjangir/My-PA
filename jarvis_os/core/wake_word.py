import threading
import time
import io
import wave
import logging
import json
import os
import numpy as np

try:
    import sounddevice as sd
    from openwakeword.model import Model
    OPENWAKEWORD_AVAILABLE = True
except ImportError:
    OPENWAKEWORD_AVAILABLE = False

logger = logging.getLogger("J.A.R.V.I.S")

# Global singleton daemon reference
_daemon = None

WAKE_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "wake_config.json")

ALLOWED_COMMANDS = {
    "morning brief",
    "resume session",
    "open github",
    "open linkedin",
    "open gmail",
    "open vs code",
    "open dashboard",
    "analyze screen",
    "start work mode",
    "what should i do today"
}

def clean_command(cmd: str) -> str:
    """Removes punctuation and normalizes."""
    import string
    return cmd.translate(str.maketrans('', '', string.punctuation)).strip().lower()

class WakeWordDaemon:
    def __init__(self, chat_service, stt_service):
        self.chat_service = chat_service
        self.stt_service = stt_service
        
        self.is_running = False
        self.thread = None
        self.last_wake = None
        
        self.enabled = False
        self._load_config()

    def _load_config(self):
        try:
            if os.path.exists(WAKE_CONFIG_FILE):
                with open(WAKE_CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.enabled = data.get("wake_word_enabled", False)
        except Exception as e:
            logger.error(f"[WakeWord] Config load error: {e}")

    def _save_config(self):
        try:
            with open(WAKE_CONFIG_FILE, 'w') as f:
                json.dump({"wake_word_enabled": self.enabled}, f)
        except Exception as e:
            logger.error(f"[WakeWord] Config save error: {e}")

    def toggle(self):
        self.enabled = not self.enabled
        self._save_config()
        from jarvis_os.core.usage import track_event
        if self.enabled:
            track_event("wake_toggle_on")
        else:
            track_event("wake_toggle_off")
        return self.enabled

    def start(self):
        if not OPENWAKEWORD_AVAILABLE:
            logger.warning("[WakeWord] Dependencies missing. Run: pip install openwakeword sounddevice numpy scipy")
            return
            
        if self.thread and self.thread.is_alive():
            return
            
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="WakeWordDaemon")
        self.thread.start()
        logger.info("[WakeWord] Daemon thread started.")

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
            logger.info("[WakeWord] Daemon thread stopped.")

    def _run_loop(self):
        try:
            owm = Model(wakeword_models=['hey_jarvis'], inference_framework="onnx")
        except Exception as e:
            logger.error(f"[WakeWord] Failed to load ONNX model: {e}")
            return
            
        CHUNK = 1280
        FORMAT = 'int16'
        CHANNELS = 1
        RATE = 16000
        
        RECORD_SECONDS = 10
        MAX_RECORD_FRAMES = int(RATE / CHUNK * RECORD_SECONDS)
        
        try:
            with sd.InputStream(samplerate=RATE, channels=CHANNELS, dtype=FORMAT, blocksize=CHUNK) as stream:
                while self.is_running:
                    if not self.enabled:
                        time.sleep(1)
                        continue
                    
                    data, overflowed = stream.read(CHUNK)
                    audio_array = np.frombuffer(data, dtype=np.int16)
                    
                    prediction = owm.predict(audio_array)
                    model_key = list(prediction.keys())[0]
                    score = prediction[model_key]
                    
                    if score > 0.5:
                        from jarvis_os.core.usage import track_event
                        track_event("wake_detected")
                        
                        logger.info(f"[WakeWord] 'Hey Jarvis' detected! Score: {score}")
                        import datetime
                        self.last_wake = datetime.datetime.now().strftime("%I:%M %p")
                        
                        frames = []
                        for _ in range(MAX_RECORD_FRAMES):
                            if not self.is_running or not self.enabled:
                                break
                            cmd_data, _ = stream.read(CHUNK)
                            frames.append(cmd_data)
                            
                        self._process_audio(frames, RATE, CHANNELS)
                        owm.reset()
                        
        except Exception as e:
            logger.error(f"[WakeWord] Microphone error: {e}")

    def _process_audio(self, frames, rate, channels):
        audio_data = np.concatenate(frames)
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(audio_data.tobytes())
            
        wav_bytes = wav_io.getvalue()
        wav_io.close()
        
        del frames
        del audio_data
        
        if not self.stt_service or not self.stt_service.is_available:
            logger.warning("[WakeWord] STT unavailable")
            return
            
        result = self.stt_service.transcribe(wav_bytes, filename="wake_command.wav")
        text = result.get("text", "")
        
        if not text:
            logger.info("[WakeWord] No command detected.")
            from jarvis_os.core.usage import track_event
            track_event("wake_timeout")
            self._speak("No command detected Boss.")
            return
            
        logger.info(f"[WakeWord] Recognized command: {text}")
        cleaned = clean_command(text)
        
        if cleaned not in ALLOWED_COMMANDS:
            logger.info(f"[WakeWord] Command not supported: {cleaned}")
            self._speak("Sorry Boss, I don't support that command yet.")
            return
            
        from jarvis_os.core.usage import track_event
        track_event("wake_command_executed")
        
        logger.info("[WakeWord] Executing command via existing pipeline.")
        if self.chat_service:
            try:
                session_id = self.chat_service.get_or_create_session("wakeword_session")
                stream = self.chat_service.process_jarvis_message_stream(session_id, cleaned)
                
                full_response = ""
                for chunk in stream:
                    if isinstance(chunk, str):
                        full_response += chunk
                
                if full_response.strip():
                    self._speak(full_response.strip())
                    
            except Exception as e:
                logger.error(f"[WakeWord] Execution failed: {e}")
        else:
            logger.warning("[WakeWord] No chat_service attached!")
            
    def _speak(self, text: str):
        """
        Speak a response locally using the shared JARVIS TTS pipeline.
        Routes through app.tts_utils — same voice, same config, one architecture.
        Runs in a daemon thread so it never blocks the wake word loop.
        """
        from config import TTS_VOICE, TTS_RATE

        def _run():
            try:
                from app.tts_utils import generate_tts_bytes, play_audio_locally
                audio_bytes = generate_tts_bytes(text, TTS_VOICE, TTS_RATE)
                play_audio_locally(audio_bytes)
            except Exception as e:
                logger.error(f"[WakeWord] TTS error: {e}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()



def init_wake_word_daemon(chat_service, stt_service):
    global _daemon
    if _daemon is None:
        _daemon = WakeWordDaemon(chat_service, stt_service)
        _daemon.start()

def shutdown_wake_word_daemon():
    global _daemon
    if _daemon is not None:
        _daemon.stop()
        
def get_wake_word_daemon() -> WakeWordDaemon:
    return _daemon
