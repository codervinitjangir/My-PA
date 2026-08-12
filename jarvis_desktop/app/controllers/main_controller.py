import asyncio
import base64
import io
import os
import subprocess
import sys
import threading
from PySide6.QtCore import QObject, Signal
from PIL import ImageGrab

from jarvis_desktop.app.services.system_state import SystemState
from jarvis_desktop.app.services.desktop_state import DesktopState


class OrbManager:
    """Manages the Ultron Orb Next.js dev server process lifecycle."""

    def __init__(self):
        self._process: subprocess.Popen | None = None
        # Resolve the ultron-orb directory relative to this file's project root
        self._orb_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "ultron-orb"
        )
        self._orb_dir = os.path.normpath(self._orb_dir)

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self):
        if self.is_running:
            return
        npm = "npm.cmd" if sys.platform == "win32" else "npm"
        self._process = subprocess.Popen(
            [npm, "run", "dev"],
            cwd=self._orb_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )

    def stop(self):
        if not self.is_running:
            return
        if sys.platform == "win32":
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(self._process.pid)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            self._process.terminate()
        self._process = None


class MainController(QObject):
    """
    Main Application Controller integrating SystemState & DesktopState reactive observations
    and Async Backend Services.
    """
    audio_recorded = Signal(bytes)

    def __init__(self, main_window, backend_service, system_state: SystemState = None, desktop_state: DesktopState = None, parent=None):
        super().__init__(parent)
        self.win = main_window
        self.backend = backend_service
        self.sys_state = system_state or SystemState(self)
        self.desk_state = desktop_state or DesktopState(self)

        self.is_listening = False
        self._one_shot_mic = False
        self.tts_enabled = True
        self.orb = OrbManager()   # Orb process manager — starts/stops on demand

        self._subscribe_state()
        self._connect_ui_signals()
        self._connect_backend_signals()

    def _subscribe_state(self):
        """Observe SystemState and DesktopState changes to update UI widgets reactively"""
        self.sys_state.backend_status_changed.connect(self._on_connection_status_changed)
        self.sys_state.voice_state_changed.connect(self._on_voice_state_changed)
        self.desk_state.current_mode_changed.connect(self._on_mode_changed)

    def _connect_ui_signals(self):
        # Header & Connectors signals
        self.win.header.mode_changed.connect(self.desk_state.set_current_mode)
        self.win.header.activity_toggled.connect(self.win.toggle_sidebar)
        self.win.header.settings_requested.connect(self.win.show_settings)
        self.win.header.new_chat_requested.connect(self._on_new_chat)
        self.win.connectors_panel.mode_selected.connect(self.desk_state.set_current_mode)

        # Input Bar signals
        self.win.input_bar.send_requested.connect(self._on_send_message)
        self.win.input_bar.cam_toggled.connect(self._on_camera_toggled)
        self.win.input_bar.mic_toggled.connect(self._on_mic_toggled)
        self.win.input_bar.tts_toggled.connect(self._on_tts_toggled)
        self.win.input_bar.ptt_pressed.connect(self._on_ptt_pressed)
        self.win.input_bar.voice_mode_stop_requested.connect(self._on_voice_mode_stop)

        # Also allow launching orb from the placeholder panel button
        self.win.orb_widget.launch_requested.connect(self._on_orb_toggled)
        self.win.orb_widget.close_requested.connect(self._on_orb_toggled)

        self.win.chat_panel.chip_clicked.connect(self._on_send_message)
        self.win.chat_panel.settings_requested.connect(self.win.show_settings)

        # Command Center signals
        self.win.command_center.action_triggered.connect(self._on_command_action)

        self.audio_recorded.connect(self._on_audio_recorded)

        # Settings Dialog signals
        self.win.settings_dialog.setting_changed.connect(self.desk_state.set_setting)

    def _connect_backend_signals(self):
        self.backend.status_changed.connect(
            lambda is_online: self.sys_state.set_backend_status("online" if is_online else "offline")
        )
        self.backend.dashboard_updated.connect(self._on_dashboard_updated)
        self.backend.chat_chunk_received.connect(self._on_chat_chunk)
        self.backend.chat_response_received.connect(self._on_chat_response)
        self.backend.error_occurred.connect(self._on_error)
        self.backend.latency_updated.connect(self.win.chat_panel.update_latency)

    def _on_chat_chunk(self, chunk: str):
        """Append incoming streaming token chunk to chat stream"""
        if not hasattr(self, "_current_assistant_bubble") or self._current_assistant_bubble is None:
            self._current_assistant_bubble = self.win.chat_panel.add_assistant_message("", timestamp="")
        if hasattr(self, "_current_assistant_bubble") and self._current_assistant_bubble:
            self._current_assistant_bubble.append_chunk(chunk)

    def _on_connection_status_changed(self, status: str):
        self.win.header.set_system_status(status)
        self.win.orb_widget.set_voice_state(status)

    def _on_voice_state_changed(self, voice_state: str):
        if voice_state != "idle":
            self.win.header.set_system_status(voice_state)
            self.win.orb_widget.set_voice_state(voice_state)
        else:
            self.win.header.set_system_status(self.sys_state.backend_status)
            self.win.orb_widget.set_voice_state(self.sys_state.backend_status)

    def _on_new_chat(self):
        self._current_assistant_bubble = None
        self.win.chat_panel.clear_messages()
        self.win.sidebar.clear_flow()

    def _on_send_message(self, text: str, is_voice: bool = False):
        self._current_assistant_bubble = None

        # Add user message bubble
        self.win.chat_panel.add_user_message(text)

        # Log query step in activity timeline
        self.win.sidebar.clear_flow()
        self.win.sidebar.add_flow_step("1", "Query detected", text)
        self.win.sidebar.add_flow_step("2", "Primary Brain", "Processing query...")

        # Update voice/execution status
        self.sys_state.set_voice_state("thinking")

        # Dispatch async streaming HTTP request for instant token response (<500ms)
        asyncio.create_task(self.backend.stream_chat_message(text, self.desk_state.current_mode, is_voice=is_voice))

    def _on_camera_toggled(self):
        """Capture screen screenshot and dispatch to vision brain"""
        try:
            self.win.input_bar.set_cam_active(True)
            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            raw_bytes = buf.getvalue()
            buf.close()
            img.close()

            b64_str = base64.b64encode(raw_bytes).decode("utf-8")
            self.win.chat_panel.add_user_message("📷 [Analyzing Current Screen...]")
            self.sys_state.set_voice_state("thinking")
            
            asyncio.create_task(self.backend.analyze_vision(b64_str))
        except Exception as e:
            self.win.chat_panel.add_assistant_message(f"Screen capture failed: {str(e)}")
        finally:
            self.win.input_bar.set_cam_active(False)

    def _on_ptt_pressed(self, is_down: bool):
        if is_down and not self.is_listening:
            self._one_shot_mic = True
            self._on_mic_toggled()

    def _on_mic_toggled(self):
        """Toggle microphone audio recording for voice input"""
        if self.is_listening:
            self.is_listening = False
            self._one_shot_mic = False
            self.win.input_bar.set_mic_active(False)
            self.sys_state.set_voice_state("idle")
        else:
            self.is_listening = True
            self.win.input_bar.set_mic_active(True)
            self.sys_state.set_voice_state("listening")
            threading.Thread(target=self._record_and_transcribe, daemon=True).start()

    # ── Hands-Free Voice Mode ──────────────────────────────────────────────────
    def _on_mode_changed(self, mode: str):
        """React when user selects a mode in the connectors sidebar."""
        if mode == "voice":
            self._start_hands_free_listening()
        else:
            self._stop_hands_free_listening()

    def _start_hands_free_listening(self):
        """Start continuous (hands-free) mic listening. Loops automatically after each utterance."""
        if self.is_listening:
            return
        self._one_shot_mic = False
        self.is_listening = True
        self.win.input_bar.set_mic_active(True)
        self.win.input_bar.set_voice_mode_active(True)
        self.win.connectors_panel.set_active_mode("voice")
        self.sys_state.set_voice_state("listening")
        threading.Thread(target=self._record_and_transcribe, daemon=True).start()

    def _stop_hands_free_listening(self):
        """Stop continuous listening and restore PTT mode."""
        self.is_listening = False
        self._one_shot_mic = False
        self.win.input_bar.set_mic_active(False)
        self.win.input_bar.set_voice_mode_active(False)
        self.sys_state.set_voice_state("idle")

    def _on_voice_mode_stop(self):
        """User clicked the '🔴 STOP LISTENING' button — exit hands-free mode."""
        self._stop_hands_free_listening()
        # Revert desk state and sidebar highlight to 'text'
        self.desk_state.set_current_mode("text")
        self.win.connectors_panel.set_active_mode("text")


    def _record_and_transcribe(self):
        """Record audio dynamically using VAD to minimize latency"""
        try:
            import sounddevice as sd
            import wave
            import numpy as np
            import time

            RATE = 16000
            CHANNELS = 1
            CHUNK_DURATION = 0.1
            CHUNK_SAMPLES = int(CHUNK_DURATION * RATE)
            SILENCE_LIMIT = 0.6  # seconds of silence to mark end of sentence
            ENERGY_THRESHOLD = 50  # Lowered threshold to accommodate quiet microphones

            # --- ADAPTIVE CALIBRATION ---
            print("[Mic] Calibrating room noise for 1 second...")
            try:
                noise_rec = sd.rec(int(1 * RATE), samplerate=RATE, channels=CHANNELS, dtype=np.int16)
                sd.wait()
                room_noise_energy = np.sqrt(np.mean(noise_rec.astype(np.float64)**2))
                # Use 2x noise as threshold, floor of 25, hard ceiling of 60
                # so a quiet laptop mic can still trigger on normal speech
                ENERGY_THRESHOLD = min(max(room_noise_energy * 2, 25), 60)
                print(f"[Mic] Room noise: {room_noise_energy:.2f} -> Threshold: {ENERGY_THRESHOLD:.2f}")
            except Exception as e:
                ENERGY_THRESHOLD = 30
                print(f"[Mic] Calibration failed: {e}. Defaulting to 30.")
            # ------------------------------

            while self.is_listening:
                audio_buffer = []
                silence_timer = 0.0
                has_spoken = False

                while self.is_listening:
                    if self.sys_state.voice_state not in ("listening", "idle"):
                        has_spoken = False
                        silence_timer = 0.0
                        audio_buffer.clear()
                        time.sleep(0.1)
                        continue

                    recording = sd.rec(CHUNK_SAMPLES, samplerate=RATE, channels=CHANNELS, dtype=np.int16)
                    sd.wait()

                    if not self.is_listening:
                        break

                    energy = np.sqrt(np.mean(recording.astype(np.float64)**2))

                    # Temporary energy logging
                    print(f"[Mic Energy] {energy:.2f} (Threshold: {ENERGY_THRESHOLD:.2f})")

                    if energy > ENERGY_THRESHOLD:
                        has_spoken = True
                        silence_timer = 0.0
                        audio_buffer.append(recording)
                    elif has_spoken:
                        silence_timer += CHUNK_DURATION
                        audio_buffer.append(recording)
                        if silence_timer >= SILENCE_LIMIT:
                            break  # End of sentence
                    else:
                        pass  # Waiting for speech to start

                if has_spoken and len(audio_buffer) > 0:
                    full_recording = np.concatenate(audio_buffer, axis=0)

                    wav_io = io.BytesIO()
                    with wave.open(wav_io, 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(2)
                        wf.setframerate(RATE)
                        wf.writeframes(full_recording.tobytes())

                    wav_bytes = wav_io.getvalue()
                    wav_io.close()

                    self.audio_recorded.emit(wav_bytes)

                    # Brief pause so we don't immediately start recording our own TTS
                    time.sleep(0.5)

        except Exception as e:
            print(f"[Mic Recording Error]: {e}")
            self.audio_recorded.emit(b"")

    def _on_audio_recorded(self, wav_bytes: bytes):
        if wav_bytes:
            # One-shot PTT: stop listening immediately after capture
            if getattr(self, '_one_shot_mic', False) and self.is_listening:
                self._on_mic_toggled()

            asyncio.create_task(self._process_stt(wav_bytes))
        else:
            if not self.is_listening:
                self.sys_state.set_voice_state("idle")
            elif self.desk_state.current_mode == "voice":
                # Empty/silent recording in hands-free mode — stay in Listening state
                self.sys_state.set_voice_state("listening")

    async def _process_stt(self, wav_bytes: bytes):
        text = await self.backend.transcribe_audio(wav_bytes)
        if text:
            self._on_send_message(text, is_voice=True)
        else:
            # In voice mode, don't go idle — return to listening so the loop continues
            if self.desk_state.current_mode == "voice" and self.is_listening:
                self.sys_state.set_voice_state("listening")
            else:
                self.sys_state.set_voice_state("idle")

    def _on_tts_toggled(self):
        """Toggle assistant voice synthesis output"""
        self.tts_enabled = not self.tts_enabled
        self.win.input_bar.set_tts_enabled(self.tts_enabled)

    def _on_chat_response(self, data: dict):
        self.sys_state.set_backend_status("online")

        # In hands-free voice mode, return to listening after each response
        if self.desk_state.current_mode == "voice" and self.is_listening:
            self.sys_state.set_voice_state("listening")
        else:
            self.sys_state.set_voice_state("idle")

        response_text = data.get("response", "")
        flow = data.get("flow", [])
        latency = data.get("latency_metrics", {})

        lat_str = ""
        if latency:
            stt = latency.get("stt", 0)
            ttfa = latency.get("ttfa", 0)
            lat_str = f"⚡ STT {stt}ms • TTFA {ttfa}ms"

        # If streaming didn't create a bubble yet, add one now
        if not hasattr(self, "_current_assistant_bubble") or self._current_assistant_bubble is None:
            self.win.chat_panel.add_assistant_message(response_text, latency_info=lat_str)
        self._current_assistant_bubble = None

        for step in flow:
            num = str(step.get("step", ""))
            title = step.get("title", "")
            detail = step.get("detail", "")
            self.win.sidebar.add_flow_step(num, title, detail)

        if self.tts_enabled and response_text:
            asyncio.create_task(self._play_tts_response(response_text))

    async def _play_tts_response(self, text: str):
        """Fetch and play TTS audio for assistant reply"""
        try:
            clean_text = text[:300].replace("*", "").replace("#", "").replace("`", "").strip()
            if not clean_text:
                return

            audio_bytes = await self.backend.synthesize_speech(clean_text)
            if audio_bytes:
                import io
                import pygame
                
                if not pygame.mixer.get_init():
                    pygame.mixer.init()

                audio_stream = io.BytesIO(audio_bytes)
                pygame.mixer.music.load(audio_stream)
                pygame.mixer.music.play()
        except Exception as e:
            print(f"[TTS Playback Error]: {e}")

    def _on_dashboard_updated(self, data: dict):
        if "metrics" in data:
            self.win.command_center.metric_card.update_metrics(data["metrics"])

    def _on_command_action(self, action_cmd: str):
        if action_cmd == "Refresh Dashboard":
            asyncio.create_task(self.backend.fetch_dashboard())
        elif action_cmd == "Morning Brief":
            asyncio.create_task(self.backend.fetch_briefing())
        elif action_cmd == "Analyze Screen":
            self._on_camera_toggled()
        else:
            self._on_send_message(action_cmd)

    def _on_error(self, err_msg: str):
        self.sys_state.set_voice_state("idle")
        print(f"[MainController Error]: {err_msg}")
        self.win.chat_panel.add_assistant_message(f"⚠️ Error: {err_msg}")

    # ── Orb Toggle ────────────────────────────────────────────────────────────
    def _on_orb_toggled(self):
        """Start or stop the Ultron Orb Next.js dev server on demand."""
        if self.orb.is_running:
            self.orb.stop()
            self.win.orb_widget.hide_orb()
            self.win.chat_panel.add_assistant_message(
                "🌀 Ultron Orb stopped. RAM freed."
            )
        else:
            self.orb.start()
            self.win.orb_widget.show_orb()
            self.win.chat_panel.add_assistant_message(
                "🌀 Ultron Orb starting... open http://localhost:3000 in a moment."
            )
