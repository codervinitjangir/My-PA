import asyncio
import base64
import io
import tempfile
import threading
from PySide6.QtCore import QObject, Signal
from PIL import ImageGrab

from jarvis_desktop.app.services.system_state import SystemState
from jarvis_desktop.app.services.desktop_state import DesktopState

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
        self.tts_enabled = True

        self._subscribe_state()
        self._connect_ui_signals()
        self._connect_backend_signals()

    def _subscribe_state(self):
        """Observe SystemState and DesktopState changes to update UI widgets reactively"""
        self.sys_state.backend_status_changed.connect(self._on_connection_status_changed)
        self.sys_state.voice_state_changed.connect(self._on_voice_state_changed)

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
        self.backend.latency_updated.connect(self.win.connectors_panel.update_latency)

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

    def _on_send_message(self, text: str):
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
        asyncio.create_task(self.backend.stream_chat_message(text, self.desk_state.current_mode))

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

    def _on_mic_toggled(self):
        """Toggle microphone audio recording for voice input"""
        if self.is_listening:
            self.is_listening = False
            self.win.input_bar.set_mic_active(False)
            self.sys_state.set_voice_state("idle")
        else:
            self.is_listening = True
            self.win.input_bar.set_mic_active(True)
            self.sys_state.set_voice_state("listening")
            threading.Thread(target=self._record_and_transcribe, daemon=True).start()

    def _record_and_transcribe(self):
        """Record audio from microphone for 3 seconds and emit recorded signal"""
        try:
            import sounddevice as sd
            import wave
            import numpy as np

            RATE = 16000
            CHANNELS = 1
            DURATION = 3  # seconds

            recording = sd.rec(int(DURATION * RATE), samplerate=RATE, channels=CHANNELS, dtype=np.int16)
            sd.wait()

            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(RATE)
                wf.writeframes(recording.tobytes())

            wav_bytes = wav_io.getvalue()
            wav_io.close()

            self.audio_recorded.emit(wav_bytes)
        except Exception as e:
            print(f"[Mic Recording Error]: {e}")
            self.audio_recorded.emit(b"")

    def _on_audio_recorded(self, wav_bytes: bytes):
        self.is_listening = False
        self.win.input_bar.set_mic_active(False)
        if wav_bytes:
            asyncio.create_task(self._process_stt(wav_bytes))
        else:
            self.sys_state.set_voice_state("idle")

    async def _process_stt(self, wav_bytes: bytes):
        text = await self.backend.transcribe_audio(wav_bytes)
        if text:
            self._on_send_message(text)
        else:
            self.sys_state.set_voice_state("idle")

    def _on_tts_toggled(self):
        """Toggle assistant voice synthesis output"""
        self.tts_enabled = not self.tts_enabled
        self.win.input_bar.set_tts_enabled(self.tts_enabled)

    def _on_chat_response(self, data: dict):
        self.sys_state.set_voice_state("idle")
        self.sys_state.set_backend_status("online")

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
                import os, tempfile
                fd, temp_path = tempfile.mkstemp(suffix=".mp3")
                os.write(fd, audio_bytes)
                os.close(fd)  # Close file descriptor so Windows releases file lock

                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init()

                pygame.mixer.music.load(temp_path)
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
