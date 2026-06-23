import threading
import time
import io
import wave
import logging
import json
import os
import random
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

# ── VAD tuning ─────────────────────────────────────────────────────────────────
# Lower threshold = more sensitive; raise if getting false positives
WAKE_SCORE_THRESHOLD   = 0.15   # openwakeword hey_jarvis fires 0.3–0.8 typically
SPEECH_ENERGY_THRESHOLD = 20
SILENCE_CHUNK_LIMIT    = 24   # ~1.9 s of silence ends recording
MAX_RECORD_SECONDS     = 10
POST_DETECT_COOLDOWN   = 0.5  # seconds to drain mic buffer after detection


def clean_command(cmd: str) -> str:
    """Removes punctuation and normalizes."""
    import string
    return cmd.translate(str.maketrans('', '', string.punctuation)).strip().lower()


class WakeWordDaemon:
    def __init__(self, chat_service, stt_service):
        self.chat_service = chat_service
        self.stt_service  = stt_service

        self.is_running = False
        self.thread     = None
        self.last_wake  = None
        self._busy      = False   # True while STT/LLM/TTS is running
        self._history   = []      # list of {type, text, response, time}

        self.enabled = False
        self._load_config()

    @property
    def state(self) -> str:
        """Current daemon state for UI display."""
        if not self.enabled:
            return "off"
        if not (self.thread and self.thread.is_alive()):
            return "unavailable"
        if self._busy:
            return "processing"
        return "listening"

    # ── Config ─────────────────────────────────────────────────────────────────

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
        track_event("wake_toggle_on" if self.enabled else "wake_toggle_off")
        return self.enabled

    # ── Lifecycle ──────────────────────────────────────────────────────────────

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

    # ── Main Loop ──────────────────────────────────────────────────────────────

    def _run_loop(self):
        try:
            model_path = os.path.join(os.path.dirname(__file__), "models", "hey_jarvis_v0.1.onnx")
            owm = Model(wakeword_models=[model_path], inference_framework="onnx")
        except Exception as e:
            logger.error(f"[WakeWord] Failed to load model: {e}")
            return

        CHUNK    = 1280
        CHANNELS = 1
        RATE     = 16000
        MAX_FRAMES = int(RATE / CHUNK * MAX_RECORD_SECONDS)

        try:
            with sd.InputStream(samplerate=RATE, channels=CHANNELS, dtype='int16', blocksize=CHUNK) as stream:
                while self.is_running:
                    if not self.enabled:
                        time.sleep(1)
                        continue

                    data, _ = stream.read(CHUNK)
                    audio_array = np.frombuffer(data, dtype=np.int16)

                    prediction = owm.predict(audio_array)
                    score = list(prediction.values())[0]

                    if score > 0.05:
                        logger.info(f"[WakeWord] (Debug) Score: {score:.3f} | RMS: {np.sqrt(np.mean(audio_array.astype(np.float32)**2)):.1f}")

                    if score > WAKE_SCORE_THRESHOLD and not self._busy:
                        from jarvis_os.core.usage import track_event
                        track_event("wake_detected")

                        import datetime
                        self.last_wake = datetime.datetime.now().strftime("%I:%M %p")
                        logger.info(f"[WakeWord] ✅ Wake word detected! Score: {score:.2f}")

                        # ⚡ Interrupt any currently playing JARVIS TTS immediately
                        try:
                            from app.tts_utils import stop_local_tts
                            stop_local_tts()
                        except Exception:
                            pass

                        # Non-blocking chime — recording starts immediately
                        self._chime()

                        # Record with VAD — stop as soon as user goes quiet
                        frames = self._record_with_vad(stream, CHUNK, MAX_FRAMES)
                        logger.info(f"[WakeWord] 🎤 Captured {len(frames)} chunks")

                        # Process in background thread — loop keeps listening immediately
                        threading.Thread(
                            target=self._process_audio_safe,
                            args=(frames, RATE, CHANNELS),
                            daemon=True,
                            name="WakeProcess"
                        ).start()

                        # Reset model + drain mic buffer
                        owm.reset()
                        time.sleep(POST_DETECT_COOLDOWN)

        except Exception as e:
            logger.error(f"[WakeWord] Microphone error: {e}")

    # ── VAD Recording ──────────────────────────────────────────────────────────

    def _record_with_vad(self, stream, chunk_size: int, max_frames: int) -> list:
        """
        Record audio until either:
          - SILENCE_CHUNK_LIMIT consecutive silent chunks (user stopped speaking), or
          - max_frames hard cap.
        Returns list of raw audio frames.
        """
        frames          = []
        silent_chunks   = 0
        speech_detected = False

        for _ in range(max_frames):
            if not self.is_running or not self.enabled:
                break
            data, _ = stream.read(chunk_size)
            frames.append(data)

            audio = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            rms   = np.sqrt(np.mean(audio ** 2))

            if rms > SPEECH_ENERGY_THRESHOLD:
                speech_detected = True
                silent_chunks   = 0
            elif speech_detected:
                silent_chunks += 1
                if silent_chunks >= SILENCE_CHUNK_LIMIT:
                    logger.info("[WakeWord] 🔇 Silence detected — stopping recording early.")
                    break

        return frames

    # ── Audio Processing ───────────────────────────────────────────────────────

    def _process_audio_safe(self, frames: list, rate: int, channels: int):
        """Wrapper that sets/clears _busy flag around _process_audio."""
        self._busy = True
        try:
            self._process_audio(frames, rate, channels)
        except Exception as e:
            logger.error(f"[WakeWord] _process_audio error: {e}")
        finally:
            self._busy = False

    def _process_audio(self, frames: list, rate: int, channels: int):
        """
        Two-path dispatch:
          Case 1 — "Jarvis" (standalone invocation, no command):
              transcription is empty → JARVIS greets and stands by.
          Case 2 — "Hey Jarvis, open GitHub" (inline command):
              transcription has text → route directly to chat pipeline.
        """
        if not frames:
            self._speak_case1()
            return

        audio_data = np.concatenate([np.frombuffer(f, dtype=np.int16) for f in frames])
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(audio_data.tobytes())

        wav_bytes = wav_io.getvalue()
        wav_io.close()
        del frames, audio_data

        if not self.stt_service or not self.stt_service.is_available:
            logger.warning("[WakeWord] STT unavailable")
            self._speak("Sorry Boss, speech recognition is unavailable right now.")
            return

        result = self.stt_service.transcribe(wav_bytes, filename="wake_command.wav")
        text   = (result.get("text") or "").strip()

        if not text:
            # ── Case 1: standalone "Hey Jarvis" with no command ────────────────
            logger.info("[WakeWord] Case 1 — No command heard. Greeting.")
            self._speak_case1()
        else:
            # ── Case 2: inline command spoken with the wake word ───────────────
            logger.info(f"[WakeWord] Case 2 — Inline command: '{text}'")
            from jarvis_os.core.usage import track_event
            track_event("wake_command_executed")
            self._execute_command(text)

    def _speak_case1(self):
        """Greeting when user just said 'Hey Jarvis' with no command."""
        greetings = [
            "Hey Boss! What can I do for you?",
            "Yes Boss, I'm listening.",
            "At your service, Boss. Go ahead.",
            "Hey! How can I help?",
            "Yes? I'm here, Boss.",
        ]
        reply = random.choice(greetings)
        self._log_history("greeting", "", reply)
        self._speak(reply)

    def _execute_command(self, text: str):
        """
        Route an inline command.
        Fast-path: scroll commands are handled locally in <50ms, no LLM.
        Fallback: everything else goes to the chat pipeline.
        """
        # ── Fast path: scroll ───────────────────────────────────────────────
        try:
            from jarvis_os.desktop_action.scroll_controller import execute_scroll_command
            scroll_reply = execute_scroll_command(text)
            if scroll_reply:
                logger.info(f"[WakeWord] 📜 Scroll command: '{text}' → '{scroll_reply}'")
                self._speak(scroll_reply)
                return
        except Exception as e:
            logger.error(f"[WakeWord] Scroll handler error: {e}")

        # ── Chat pipeline: everything else ──────────────────────────────────
        if not self.chat_service:
            logger.warning("[WakeWord] No chat_service attached!")
            return
        try:
            session_id    = self.chat_service.get_or_create_session("wakeword_session")
            stream        = self.chat_service.process_jarvis_message_stream(session_id, text)
            full_response = ""
            for chunk in stream:
                if isinstance(chunk, str):
                    full_response += chunk

            if full_response.strip():
                logger.info(f"[WakeWord] 🔊 Speaking response ({len(full_response)} chars)")
                self._log_history("command", text, full_response.strip())
                self._speak(full_response.strip())
            else:
                logger.warning("[WakeWord] Chat pipeline returned empty response.")
        except Exception as e:
            logger.error(f"[WakeWord] Execution failed: {e}")
            err_msg = "Sorry Boss, something went wrong."
            self._log_history("error", text, err_msg)
            self._speak(err_msg)

    def _log_history(self, entry_type: str, command: str, response: str):
        """Append an interaction to the history ring buffer."""
        import datetime
        self._history.append({
            "type":     entry_type,
            "command":  command,
            "response": response,
            "time":     datetime.datetime.now().strftime("%I:%M %p"),
        })
        self._history = self._history[-20:]  # keep last 20

    # ── TTS Helpers ────────────────────────────────────────────────────────────

    def _chime(self):
        """
        Non-blocking two-tone chime — immediate audio feedback that JARVIS
        heard the wake word. Runs in a background thread so recording starts
        at the same moment without waiting for the sound to finish.
        """
        def _play():
            try:
                import platform
                if platform.system() == "Windows":
                    import winsound
                    winsound.Beep(700, 100)
                    winsound.Beep(1000, 150)
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()

    def _speak(self, text: str):
        """
        Non-blocking TTS — runs in a daemon thread so it never stalls
        the wake word detection loop.
        """
        from config import TTS_VOICE, TTS_RATE

        def _run():
            try:
                from app.tts_utils import generate_tts_bytes, play_audio_locally
                play_audio_locally(generate_tts_bytes(text, TTS_VOICE, TTS_RATE))
            except Exception as e:
                logger.error(f"[WakeWord] TTS error: {e}")

        threading.Thread(target=_run, daemon=True).start()


# ── Module-level helpers ────────────────────────────────────────────────────────

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
