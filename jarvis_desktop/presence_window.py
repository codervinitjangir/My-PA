# jarvis_desktop/presence_window.py

import json
import urllib.request
import urllib.parse
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QDialog, QApplication
)
from PySide6.QtCore import Qt, QTimer, QPoint, QUrl, QBuffer, QIODevice, QByteArray
from PySide6.QtGui import QMouseEvent, QDesktopServices
from PySide6.QtMultimedia import QMediaCaptureSession, QAudioInput, QMediaRecorder, QMediaFormat

from jarvis_desktop.styles import MAIN_STYLE, TALK_DIALOG_STYLE

API_URL = "http://127.0.0.1:8000"

class TalkDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setStyleSheet(TALK_DIALOG_STYLE)
        self.setFixedSize(250, 150)
        
        layout = QVBoxLayout(self)
        self.status_label = QLabel("🎤 Ready to record", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.record_btn = QPushButton("Hold to Talk", self)
        layout.addWidget(self.record_btn)
        
        self.close_btn = QPushButton("Cancel", self)
        self.close_btn.clicked.connect(self.reject)
        layout.addWidget(self.close_btn)
        
        # Audio Recording setup
        self.session = QMediaCaptureSession()
        self.audio_input = QAudioInput()
        self.session.setAudioInput(self.audio_input)
        
        self.recorder = QMediaRecorder()
        self.session.setRecorder(self.recorder)
        
        self.temp_file = "jarvis_temp_audio.wav"
        self.recorder.setOutputLocation(QUrl.fromLocalFile(self.temp_file))
        
        # We need a format that Groq Whisper supports
        fmt = QMediaFormat()
        fmt.setFileFormat(QMediaFormat.Wave)
        self.recorder.setMediaFormat(fmt)
        
        self.record_btn.pressed.connect(self.start_recording)
        self.record_btn.released.connect(self.stop_recording)
        
    def start_recording(self):
        self.status_label.setText("🔴 Recording...")
        self.record_btn.setText("Release to Send")
        self.recorder.record()
        
    def stop_recording(self):
        self.recorder.stop()
        self.status_label.setText("⏳ Processing...")
        self.record_btn.setEnabled(False)
        self.record_btn.setText("Sending...")
        
        # Wait a tiny bit for file to be written fully
        QTimer.singleShot(200, self.send_audio)
        
    def send_audio(self):
        try:
            with open(self.temp_file, "rb") as f:
                audio_bytes = f.read()
            
            boundary = '----JarvisBoundary123456789'
            body = bytearray()
            
            # Form-data part for 'file'
            body.extend(f'--{boundary}\r\n'.encode('utf-8'))
            body.extend(b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n')
            body.extend(b'Content-Type: audio/wav\r\n\r\n')
            body.extend(audio_bytes)
            body.extend(b'\r\n')
            
            # Optional language flag
            body.extend(f'--{boundary}\r\n'.encode('utf-8'))
            body.extend(b'Content-Disposition: form-data; name="language"\r\n\r\n')
            body.extend(b'en\r\n')
            
            body.extend(f'--{boundary}--\r\n'.encode('utf-8'))
            
            req = urllib.request.Request(f"{API_URL}/stt", data=body)
            req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
            req.add_header('Content-Length', str(len(body)))
            
            response = urllib.request.urlopen(req, timeout=10)
            res_data = json.loads(response.read().decode('utf-8'))
            text = res_data.get("text", "")
            
            if text:
                self.status_label.setText(f"Sending: {text[:20]}...")
                # Now send to chat endpoint
                self.send_to_chat(text)
            else:
                self.status_label.setText("❌ No speech detected")
                QTimer.singleShot(1500, self.reject)
                
        except Exception as e:
            self.status_label.setText("❌ Error")
            print(f"Talk Error: {e}")
            QTimer.singleShot(1500, self.reject)
            
    def send_to_chat(self, text):
        try:
            data = json.dumps({"message": text}).encode('utf-8')
            req = urllib.request.Request(f"{API_URL}/chat", data=data)
            req.add_header('Content-Type', 'application/json')
            urllib.request.urlopen(req, timeout=30)
            self.status_label.setText("✅ Sent")
            QTimer.singleShot(1000, self.accept)
        except Exception as e:
            self.status_label.setText("❌ Chat Error")
            print(f"Chat Error: {e}")
            QTimer.singleShot(1500, self.reject)

class PresenceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("presenceWindow")
        self.setFixedSize(300, 220)
        self.setStyleSheet(MAIN_STYLE)
        
        self.old_pos = None
        self._setup_ui()
        
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.fetch_data)
        self.refresh_timer.setInterval(10000) # 10s
        
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QHBoxLayout()
        self.conn_dot = QLabel("🟢", self)
        self.title_label = QLabel("JARVIS ACTIVE", self)
        self.title_label.setObjectName("headerTitle")
        
        self.hide_btn = QPushButton("✖", self)
        self.hide_btn.setFixedSize(24, 24)
        self.hide_btn.clicked.connect(self.hide)
        
        header.addWidget(self.conn_dot)
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.hide_btn)
        main_layout.addLayout(header)
        
        # Info
        self.workspace_label = QLabel("Workspace: Loading...", self)
        self.workspace_label.setObjectName("infoLabel")
        self.focus_label = QLabel("Focus: Loading...", self)
        self.focus_label.setObjectName("infoLabel")
        self.pending_label = QLabel("Pending: Loading...", self)
        self.pending_label.setObjectName("infoLabel")
        
        main_layout.addWidget(self.workspace_label)
        main_layout.addWidget(self.focus_label)
        main_layout.addWidget(self.pending_label)
        
        main_layout.addStretch()
        
        # Buttons
        btn_grid = QHBoxLayout()
        self.talk_btn = QPushButton("🎤 Talk", self)
        self.talk_btn.setObjectName("talkButton")
        self.talk_btn.clicked.connect(self.open_talk)
        
        self.brief_btn = QPushButton("☀️ Brief", self)
        self.brief_btn.clicked.connect(self.action_brief)
        
        btn_grid.addWidget(self.talk_btn)
        btn_grid.addWidget(self.brief_btn)
        main_layout.addLayout(btn_grid)
        
        btn_grid2 = QHBoxLayout()
        self.analyze_btn = QPushButton("👁 Analyze", self)
        self.analyze_btn.clicked.connect(self.action_analyze)
        
        self.dash_btn = QPushButton("📋 Dashboard", self)
        self.dash_btn.clicked.connect(self.action_dashboard)
        
        self.links_btn = QPushButton("🔗 Quick Links", self)
        
        btn_grid2.addWidget(self.analyze_btn)
        btn_grid2.addWidget(self.dash_btn)
        main_layout.addLayout(btn_grid2)

    def fetch_data(self):
        try:
            req = urllib.request.Request(f"{API_URL}/dashboard")
            response = urllib.request.urlopen(req, timeout=3)
            data = json.loads(response.read().decode('utf-8'))
            
            w_name = data.get("workspace", {}).get("name", "Jarvis")
            pending_count = len(data.get("tasks", []))
            
            self.workspace_label.setText(f"Workspace: {w_name}")
            self.pending_label.setText(f"Pending: {pending_count}")
            self.conn_dot.setText("🟢")
            
        except Exception:
            self.conn_dot.setText("🔴")

    def showEvent(self, event):
        self.fetch_data()
        self.refresh_timer.start()
        super().showEvent(event)
        
    def hideEvent(self, event):
        self.refresh_timer.stop()
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
        
    def open_talk(self):
        dlg = TalkDialog(self)
        dlg.exec()
        
    def action_brief(self):
        urllib.request.urlopen(f"{API_URL}/briefing", timeout=5)
        
    def action_analyze(self):
        QDesktopServices.openUrl(QUrl(f"{API_URL}/dashboard"))
        
    def action_dashboard(self):
        QDesktopServices.openUrl(QUrl(f"{API_URL}/dashboard"))
