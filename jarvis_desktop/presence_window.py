# jarvis_desktop/presence_window.py

import json
import os
import time
import urllib.request
import urllib.error
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication, QStackedWidget, QLineEdit, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, QPoint, QUrl
from PySide6.QtGui import QMouseEvent, QDesktopServices

from jarvis_desktop.styles import MAIN_STYLE

API_URL = "http://127.0.0.1:8000"
CONFIG_FILE = "presence_config.json"

from PySide6.QtCore import Signal

class PresenceWindow(QWidget):
    data_fetched_signal = Signal(dict)
    chat_response_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.data_fetched_signal.connect(self._on_data_fetched)
        self.chat_response_signal.connect(self._on_chat_response)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setWindowTitle("JARVIS ACTIVE")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(MAIN_STYLE)
        self.old_pos = None
        self.is_expanded = True
        self.is_backend_online = True

        self._load_config()

        self.stacked_widget = QStackedWidget(self)
        
        # Mini View
        self.mini_widget = QWidget()
        self.mini_widget.setObjectName("miniExpandWindow")
        self.mini_widget.setFixedSize(40, 40)
        mini_layout = QVBoxLayout(self.mini_widget)
        mini_layout.setContentsMargins(0, 0, 0, 0)
        self.mini_label = QLabel("🟢 J", self.mini_widget)
        self.mini_label.setObjectName("miniLabel")
        self.mini_label.setAlignment(Qt.AlignCenter)
        mini_layout.addWidget(self.mini_label)

        # Full View
        self.full_widget = QWidget()
        self.full_widget.setObjectName("presenceWindow")
        self.full_widget.setFixedSize(320, 360)
        self._setup_full_ui()

        self.stacked_widget.addWidget(self.mini_widget)
        self.stacked_widget.addWidget(self.full_widget)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stacked_widget)

        self._apply_view_state()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.fetch_data)
        self.refresh_timer.setInterval(30000) # 30s

        self.wake_status_timer = QTimer(self)
        self.wake_status_timer.timeout.connect(self._fetch_wake_status)
        self.wake_status_timer.setInterval(2000)  # 2s
        self._last_history_count = 0

        self._track("presence_open")

    def _setup_full_ui(self):
        layout = QVBoxLayout(self.full_widget)
        layout.setContentsMargins(12, 10, 12, 8)
        layout.setSpacing(3)

        # ── Header ─────────────────────────────────────────────────────────
        header = QHBoxLayout()
        self.status_icon = QLabel("🟢", self.full_widget)
        self.title_label = QLabel("JARVIS ACTIVE", self.full_widget)
        self.title_label.setObjectName("headerTitle")

        self.minimize_btn = QPushButton("—", self.full_widget)
        self.minimize_btn.setObjectName("minimizeBtn")
        self.minimize_btn.setFixedSize(18, 18)
        self.minimize_btn.setToolTip("Minimize to tray")
        self.minimize_btn.clicked.connect(self.hide)

        self.hide_btn = QPushButton("✖", self.full_widget)
        self.hide_btn.setObjectName("hideBtn")
        self.hide_btn.setFixedSize(18, 18)
        self.hide_btn.setToolTip("Close to tray")
        self.hide_btn.clicked.connect(self.hide)

        header.addWidget(self.status_icon)
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.minimize_btn)
        header.addWidget(self.hide_btn)
        layout.addLayout(header)

        # ── Info row ───────────────────────────────────────────────────────
        self.workspace_label = QLabel("Workspace: Loading...", self.full_widget)
        self.workspace_label.setObjectName("infoLabel")
        self.pending_label = QLabel("Pending: Loading...", self.full_widget)
        self.pending_label.setObjectName("infoLabel")
        self.health_label = QLabel("Latency: Checking...", self.full_widget)
        self.health_label.setObjectName("infoLabel")

        layout.addWidget(self.workspace_label)
        layout.addWidget(self.pending_label)
        layout.addWidget(self.health_label)

        # ── Wake word status bar ───────────────────────────────────────────
        self.wake_status_label = QLabel("⚫  Wake Word: Off", self.full_widget)
        self.wake_status_label.setObjectName("wakeStatusLabel")
        layout.addWidget(self.wake_status_label)

        # ── Buttons ────────────────────────────────────────────────────────
        btn_grid1 = QHBoxLayout()
        btn_grid1.setSpacing(4)
        self.talk_btn = QPushButton("🎤 Talk", self.full_widget)
        self.talk_btn.clicked.connect(self.action_talk)
        self.brief_btn = QPushButton("☀️ Brief", self.full_widget)
        self.brief_btn.clicked.connect(self.action_brief)
        self.analyze_btn = QPushButton("👁 Analyze", self.full_widget)
        self.analyze_btn.clicked.connect(self.action_analyze)
        btn_grid1.addWidget(self.talk_btn)
        btn_grid1.addWidget(self.brief_btn)
        btn_grid1.addWidget(self.analyze_btn)
        layout.addLayout(btn_grid1)

        btn_grid2 = QHBoxLayout()
        btn_grid2.setSpacing(4)
        self.dash_btn = QPushButton("📋 Dashboard", self.full_widget)
        self.dash_btn.clicked.connect(self.action_dashboard)
        self.wake_word_btn = QPushButton("⚫ Wake Word", self.full_widget)
        self.wake_word_btn.setObjectName("wakeWordBtn")
        self.wake_word_btn.clicked.connect(self.action_wake_word_toggle)
        btn_grid2.addWidget(self.dash_btn)
        btn_grid2.addWidget(self.wake_word_btn)
        layout.addLayout(btn_grid2)

        # ── Input box ──────────────────────────────────────────────────────
        self.task_input = QLineEdit(self.full_widget)
        self.task_input.setObjectName("taskInput")
        self.task_input.setPlaceholderText("Type a task and press Enter...")
        self.task_input.returnPressed.connect(self.action_submit_task)
        layout.addWidget(self.task_input)

        # ── Response area (takes all remaining space) ──────────────────────
        self.scroll_area = QScrollArea(self.full_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("scrollArea")
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)

        self.response_label = QLabel("", self.scroll_area)
        self.response_label.setObjectName("infoLabel")
        self.response_label.setWordWrap(True)
        self.response_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll_area.setWidget(self.response_label)
        layout.addWidget(self.scroll_area, 1)  # stretch=1: grows to fill remaining space

    def action_submit_task(self):
        text = self.task_input.text().strip()
        if not text:
            return
        self.task_input.clear()
        self._submit_chat(text)

    def _on_chat_response(self, chunk: str):
        if chunk == "__CLEAR__":
            self.response_label.setText("")
        elif chunk == "__DONE__":
            self.title_label.setText("JARVIS ACTIVE")
            self.status_icon.setText("🟢")
            self._set_buttons_enabled(True)
        else:
            current = self.response_label.text()
            self.response_label.setText(current + chunk)
            # Auto-scroll to bottom
            bar = self.scroll_area.verticalScrollBar()
            bar.setValue(bar.maximum())

    def _submit_chat(self, text: str):
        self.chat_response_signal.emit("__CLEAR__")
        self.title_label.setText("Thinking...")
        self.status_icon.setText("⚙")
        self._set_buttons_enabled(False)
        
        def _send_task():
            try:
                import urllib.request, json, os
                req = urllib.request.Request(
                    f"{API_URL}/chat/jarvis/stream",
                    data=json.dumps({"message": text, "tts": False, "session_id": None}).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=120) as response:
                    for line in response:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data: "):
                            try:
                                data = json.loads(line_str[6:])
                                chunk = data.get("chunk", "")
                                if chunk:
                                    self.chat_response_signal.emit(chunk)
                                actions = data.get("actions", {})
                                if actions:
                                    for url in actions.get("wopens", []) + actions.get("plays", []) + actions.get("googlesearches", []) + actions.get("youtubesearches", []):
                                        os.startfile(url)
                            except Exception as e:
                                pass
            except Exception as e:
                self.chat_response_signal.emit(f"\nError: {e}")
            finally:
                self.chat_response_signal.emit("__DONE__")
                
        import threading
        threading.Thread(target=_send_task, daemon=True).start()

    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    cfg = json.load(f)
                    if "x" in cfg and "y" in cfg:
                        self.move(cfg["x"], cfg["y"])
                    self.is_expanded = cfg.get("is_expanded", True)
        except Exception:
            pass

    def _save_config(self):
        try:
            cfg = {
                "x": self.x(),
                "y": self.y(),
                "is_expanded": self.is_expanded
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(cfg, f)
        except Exception:
            pass

    def _apply_view_state(self):
        if self.is_expanded:
            self.stacked_widget.setCurrentWidget(self.full_widget)
            self.setFixedSize(320, 360)
        else:
            self.stacked_widget.setCurrentWidget(self.mini_widget)
            self.setFixedSize(40, 40)
        self._save_config()

    def fetch_data(self):
        import threading
        t = threading.Thread(target=self._fetch_thread, daemon=True)
        t.start()

    def _fetch_thread(self):
        t0 = time.time()
        try:
            req = urllib.request.Request(f"{API_URL}/health")
            response = urllib.request.urlopen(req, timeout=3)
            response.read()
            latency = int((time.time() - t0) * 1000)
            
            # Now fetch dashboard state
            req_dash = urllib.request.Request(f"{API_URL}/dashboard")
            resp_dash = urllib.request.urlopen(req_dash, timeout=3)
            data = json.loads(resp_dash.read().decode('utf-8'))
            
            self.data_fetched_signal.emit({
                "success": True,
                "latency": latency,
                "data": data
            })
            
        except Exception:
            self.data_fetched_signal.emit({
                "success": False
            })

    def _on_data_fetched(self, result: dict):
        if result["success"]:
            data = result["data"]
            w_name = (data.get("workspace") or {}).get("name", "Jarvis")
            pending_count = len(data.get("tasks") or [])
            
            self.workspace_label.setText(f"Workspace: {w_name}")
            self.pending_label.setText(f"Pending: {pending_count}")
            self.health_label.setText(f"Latency: {result['latency']} ms")
            self.status_icon.setText("🟢")
            self.title_label.setText("JARVIS ACTIVE")
            self.mini_label.setText("🟢 J")
            
            wake = data.get("wake_word") or {}
            self._sync_wake_word_btn(wake.get("enabled", False))
                
            self._set_buttons_enabled(True)
            self.is_backend_online = True
        else:
            self.is_backend_online = False
            self.status_icon.setText("🔴")
            self.title_label.setText("JARVIS OFFLINE")
            self.health_label.setText("Latency: Offline (reconnect 60s)")
            self.mini_label.setText("🔴 J")
            self._set_buttons_enabled(False)
            # Recheck later
            QTimer.singleShot(60000, self.fetch_data)

    def _sync_wake_word_btn(self, enabled: bool):
        """Single place to set wake word button label + style."""
        if enabled:
            self.wake_word_btn.setText("🟢 Wake Word")
        else:
            self.wake_word_btn.setText("⚫ Wake Word")

    def _set_buttons_enabled(self, enabled: bool):
        self.talk_btn.setEnabled(enabled)
        self.brief_btn.setEnabled(enabled)
        self.analyze_btn.setEnabled(enabled)
        self.dash_btn.setEnabled(enabled)
        self.wake_word_btn.setEnabled(enabled)

    # ── Wake Word Status Polling ───────────────────────────────────────────────

    def _fetch_wake_status(self):
        """Poll /api/wake-word/status every 2s in a background thread."""
        import threading
        threading.Thread(target=self._wake_status_thread, daemon=True).start()

    def _wake_status_thread(self):
        try:
            import urllib.request, json
            req = urllib.request.Request(f"{API_URL}/api/wake-word/status")
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode())
            QTimer.singleShot(0, lambda: self._on_wake_status(data))
        except Exception:
            pass  # silently skip — server may not be running

    def _on_wake_status(self, data: dict):
        """Update status bar + append new wake-word conversations to response area."""
        state = data.get("state", "unavailable")

        # Update the status bar label
        _state_display = {
            "off":          "⚫  Wake Word: Off",
            "listening":    "🎤  Wake Word: Listening...",
            "processing":   "⚙️  Wake Word: Processing...",
            "unavailable":  "⚫  Wake Word: Unavailable",
        }
        self.wake_status_label.setText(_state_display.get(state, "⚫  Wake Word"))

        # Also sync the toggle button appearance
        if state in ("listening", "processing"):
            self._sync_wake_word_btn(True)
        elif state == "off":
            self._sync_wake_word_btn(False)

        # Append any new wake-word interactions to the response area
        history = data.get("history", [])
        new_count = len(history)
        if new_count > self._last_history_count:
            new_entries = history[self._last_history_count:]
            self._last_history_count = new_count
            current = self.response_label.text()
            for entry in new_entries:
                t = entry.get("time", "")
                if entry.get("type") == "greeting":
                    line = f"[{t}] 🤖 {entry.get('response', '')}"
                elif entry.get("type") == "command":
                    line = f"[{t}] 🎙 {entry.get('command', '')}\n      🤖 {entry.get('response', '')}"
                else:
                    line = f"[{t}] ⚠️ {entry.get('response', '')}"
                current = (current + "\n" + line).strip()
            self.response_label.setText(current)
            bar = self.scroll_area.verticalScrollBar()
            bar.setValue(bar.maximum())

    def showEvent(self, event):
        self.fetch_data()
        self.refresh_timer.start()
        self.wake_status_timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.refresh_timer.stop()
        self.wake_status_timer.stop()
        self._track("presence_hide")
        super().hideEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.old_pos = None
        self._save_config()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.is_expanded = not self.is_expanded
            self._apply_view_state()

    def _track(self, event_name: str):
        try:
            # We can invoke usage module or hit an endpoint. We will just hit an endpoint if available,
            # or ideally we don't do it via API if it's purely a local desktop script.
            # Wait, the API might not have a /usage tracking endpoint. Let's just run it via local python path.
            # But we are in a different process.
            # To track, we could write to the usage.py directly from here if we import it.
            # `from jarvis_os.core.usage import track_event`
            import sys
            import os
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from jarvis_os.core.usage import track_event
            track_event(event_name)
        except Exception as e:
            pass

    def action_talk(self):
        self._track("presence_voice")
        QDesktopServices.openUrl(QUrl(f"{API_URL}?action=talk"))
        
    def action_brief(self):
        self._track("presence_brief")
        self._submit_chat("Give me a daily briefing")
        
    def action_analyze(self):
        self._track("presence_analyze")
        self._submit_chat("Analyze my screen")
        
    def action_dashboard(self):
        self._track("presence_dashboard")
        QDesktopServices.openUrl(QUrl(API_URL))

    def action_wake_word_toggle(self):
        self._track("presence_wake_toggle")
        self.wake_word_btn.setEnabled(False)
        self.wake_word_btn.setText("⏳ Wake Word")
        def _toggle():
            try:
                import urllib.request, json
                req = urllib.request.Request(
                    f"{API_URL}/operator/action",
                    data=json.dumps({"action": "toggle_wake_word"}).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    is_enabled = data.get("enabled", False)
                    def _update_ui():
                        self.wake_word_btn.setEnabled(True)
                        self._sync_wake_word_btn(is_enabled)
                    QTimer.singleShot(0, _update_ui)
            except Exception as e:
                def _fail():
                    self.wake_word_btn.setEnabled(True)
                    self.wake_word_btn.setText("🔴 Wake Word")
                QTimer.singleShot(0, _fail)
        
        import threading
        threading.Thread(target=_toggle, daemon=True).start()
