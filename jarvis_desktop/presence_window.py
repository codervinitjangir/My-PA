# jarvis_desktop/presence_window.py

import json
import os
import time
import urllib.request
import urllib.error
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication, QStackedWidget
)
from PySide6.QtCore import Qt, QTimer, QPoint, QUrl
from PySide6.QtGui import QMouseEvent, QDesktopServices

from jarvis_desktop.styles import MAIN_STYLE

API_URL = "http://127.0.0.1:8000"
CONFIG_FILE = "presence_config.json"

class PresenceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
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
        self.full_widget.setFixedSize(300, 170)
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
        
        self._track("presence_open")

    def _setup_full_ui(self):
        layout = QVBoxLayout(self.full_widget)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(6)
        
        # Header
        header = QHBoxLayout()
        self.status_icon = QLabel("🟢", self.full_widget)
        self.title_label = QLabel("JARVIS ACTIVE", self.full_widget)
        self.title_label.setObjectName("headerTitle")
        
        self.hide_btn = QPushButton("✖", self.full_widget)
        self.hide_btn.setObjectName("hideBtn")
        self.hide_btn.setFixedSize(20, 20)
        self.hide_btn.clicked.connect(self.hide)
        
        header.addWidget(self.status_icon)
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.hide_btn)
        layout.addLayout(header)
        
        # Info
        self.workspace_label = QLabel("Workspace: Loading...", self.full_widget)
        self.workspace_label.setObjectName("infoLabel")
        self.pending_label = QLabel("Pending: Loading...", self.full_widget)
        self.pending_label.setObjectName("infoLabel")
        self.health_label = QLabel("Latency: Checking...", self.full_widget)
        self.health_label.setObjectName("infoLabel")
        
        layout.addWidget(self.workspace_label)
        layout.addWidget(self.pending_label)
        layout.addWidget(self.health_label)
        
        layout.addStretch()
        
        # Buttons Grid
        btn_grid1 = QHBoxLayout()
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
        self.dash_btn = QPushButton("📋 Dashboard", self.full_widget)
        self.dash_btn.clicked.connect(self.action_dashboard)
        
        self.wake_word_btn = QPushButton("🟡 Wake Word (Coming Soon)", self.full_widget)
        self.wake_word_btn.setObjectName("wakeWordBtn")
        self.wake_word_btn.setEnabled(False)
        
        btn_grid2.addWidget(self.dash_btn)
        btn_grid2.addWidget(self.wake_word_btn)
        layout.addLayout(btn_grid2)

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
            self.setFixedSize(300, 170)
        else:
            self.stacked_widget.setCurrentWidget(self.mini_widget)
            self.setFixedSize(40, 40)
        self._save_config()

    def fetch_data(self):
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
            
            w_name = data.get("workspace", {}).get("name", "Jarvis")
            pending_count = len(data.get("tasks", []))
            
            self.workspace_label.setText(f"Workspace: {w_name}")
            self.pending_label.setText(f"Pending: {pending_count}")
            self.health_label.setText(f"Latency: {latency} ms")
            self.status_icon.setText("🟢")
            self.title_label.setText("JARVIS ACTIVE")
            self.mini_label.setText("🟢 J")
            self._set_buttons_enabled(True)
            self.is_backend_online = True
            
        except Exception:
            self.is_backend_online = False
            self.status_icon.setText("🔴")
            self.title_label.setText("JARVIS OFFLINE")
            self.health_label.setText("Latency: Offline (reconnect 60s)")
            self.mini_label.setText("🔴 J")
            self._set_buttons_enabled(False)
            # Recheck later
            QTimer.singleShot(60000, self.fetch_data)

    def _set_buttons_enabled(self, enabled: bool):
        self.talk_btn.setEnabled(enabled)
        self.brief_btn.setEnabled(enabled)
        self.analyze_btn.setEnabled(enabled)
        self.dash_btn.setEnabled(enabled)
        # Wake word stays disabled
        self.wake_word_btn.setEnabled(False)

    def showEvent(self, event):
        self.fetch_data()
        self.refresh_timer.start()
        super().showEvent(event)
        
    def hideEvent(self, event):
        self.refresh_timer.stop()
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
        self.status_icon.setText("⚙")
        self.title_label.setText("Processing...")
        try:
            urllib.request.urlopen(f"{API_URL}/briefing", timeout=5)
            self.status_icon.setText("🟢")
            self.title_label.setText("JARVIS ACTIVE")
        except Exception:
            self.status_icon.setText("🔴")
            self.title_label.setText("JARVIS OFFLINE")
        
    def action_analyze(self):
        self._track("presence_analyze")
        self.status_icon.setText("⚙")
        self.title_label.setText("Processing...")
        try:
            req = urllib.request.Request(f"{API_URL}/operator/action", method="POST")
            req.add_header('Content-Type', 'application/json')
            data = json.dumps({"action": "analyze_screen"}).encode('utf-8')
            urllib.request.urlopen(req, data=data, timeout=10)
            self.status_icon.setText("🟢")
            self.title_label.setText("JARVIS ACTIVE")
        except Exception:
            self.status_icon.setText("🔴")
            self.title_label.setText("JARVIS OFFLINE")
        
    def action_dashboard(self):
        self._track("presence_dashboard")
        QDesktopServices.openUrl(QUrl(API_URL))
