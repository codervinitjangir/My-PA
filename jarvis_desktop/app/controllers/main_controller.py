# jarvis_desktop/app/controllers/main_controller.py

import asyncio
from PySide6.QtCore import QObject

from jarvis_desktop.app.services.system_state import SystemState
from jarvis_desktop.app.services.desktop_state import DesktopState

class MainController(QObject):
    """
    Main Application Controller integrating SystemState & DesktopState reactive observations
    and Async Backend Services.
    """
    def __init__(self, main_window, backend_service, system_state: SystemState = None, desktop_state: DesktopState = None, parent=None):
        super().__init__(parent)
        self.win = main_window
        self.backend = backend_service
        self.sys_state = system_state or SystemState(self)
        self.desk_state = desktop_state or DesktopState(self)

        self._subscribe_state()
        self._connect_ui_signals()
        self._connect_backend_signals()

    def _subscribe_state(self):
        """Observe SystemState and DesktopState changes to update UI widgets reactively"""
        self.sys_state.backend_status_changed.connect(self._on_connection_status_changed)
        self.sys_state.voice_state_changed.connect(self._on_voice_state_changed)

    def _connect_ui_signals(self):
        # Header signals
        self.win.header.mode_changed.connect(self.desk_state.set_current_mode)
        self.win.header.activity_toggled.connect(self.win.toggle_sidebar)
        self.win.header.settings_requested.connect(self.win.show_settings)
        self.win.header.new_chat_requested.connect(self._on_new_chat)

        # Input Bar signals
        self.win.input_bar.send_requested.connect(self._on_send_message)
        self.win.chat_panel.chip_clicked.connect(self._on_send_message)

        # Command Center signals
        self.win.command_center.action_triggered.connect(self._on_command_action)

        # Settings Dialog signals
        self.win.settings_dialog.setting_changed.connect(self.desk_state.set_setting)

    def _connect_backend_signals(self):
        self.backend.status_changed.connect(
            lambda is_online: self.sys_state.set_backend_status("online" if is_online else "offline")
        )
        self.backend.dashboard_updated.connect(self._on_dashboard_updated)
        self.backend.chat_response_received.connect(self._on_chat_response)
        self.backend.error_occurred.connect(self._on_error)

    def _on_connection_status_changed(self, status: str):
        self.win.header.set_system_status(status)

    def _on_voice_state_changed(self, voice_state: str):
        if voice_state != "idle":
            self.win.header.set_system_status(voice_state)

    def _on_new_chat(self):
        self.win.chat_panel.clear_messages()
        self.win.sidebar.clear_flow()

    def _on_send_message(self, text: str):
        # Add user message bubble
        self.win.chat_panel.add_user_message(text)

        # Log query step in activity timeline
        self.win.sidebar.clear_flow()
        self.win.sidebar.add_flow_step("1", "Query detected", text)
        self.win.sidebar.add_flow_step("2", "Primary Brain", "Processing query...")

        # Update voice/execution status
        self.sys_state.set_voice_state("thinking")

        # Dispatch async HTTP request
        asyncio.create_task(self.backend.send_chat_message(text, self.desk_state.current_mode))

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

        self.win.chat_panel.add_assistant_message(response_text, latency_info=lat_str)

        for step in flow:
            num = str(step.get("step", ""))
            title = step.get("title", "")
            detail = step.get("detail", "")
            self.win.sidebar.add_flow_step(num, title, detail)

    def _on_dashboard_updated(self, data: dict):
        if "metrics" in data:
            self.win.command_center.metric_card.update_metrics(data["metrics"])

    def _on_command_action(self, action_cmd: str):
        if action_cmd == "Refresh Dashboard":
            asyncio.create_task(self.backend.fetch_dashboard())
        elif action_cmd == "Morning Brief":
            asyncio.create_task(self.backend.fetch_briefing())
        else:
            self._on_send_message(action_cmd)

    def _on_error(self, err_msg: str):
        self.sys_state.set_voice_state("idle")
        print(f"[MainController Error]: {err_msg}")
