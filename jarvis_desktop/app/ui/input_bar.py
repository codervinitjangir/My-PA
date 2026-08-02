# jarvis_desktop/app/ui/input_bar.py

import sys
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QTextEdit, QPushButton, QWidget, QApplication
)
from PySide6.QtCore import Qt, Signal, QEvent

class InputBar(QFrame):
    """
    Sleek, uncluttered bottom control bar.
    Includes text prompt, ⭕ HOLD TO TALK PTT button, and action buttons (Cam, Mic, TTS, Send).
    """
    send_requested = Signal(str)
    mic_toggled    = Signal()
    cam_toggled    = Signal()
    tts_toggled    = Signal()
    ptt_pressed    = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("inputBar")
        self.setStyleSheet("""
            QFrame#inputBar {
                background-color: rgba(4, 8, 20, 0.95);
                border-top: 1px solid rgba(0, 217, 255, 0.12);
                padding: 4px 12px;
            }
        """)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 6, 12, 6)
        outer.setSpacing(12)

        # ── 1. Prompt Text Input ──────────────────────────────────────────────
        self.text_input = QTextEdit(self)
        self.text_input.setObjectName("messageInput")
        self.text_input.setPlaceholderText("Speak or type a command...")
        self.text_input.setFixedHeight(38)
        self.text_input.setFrameShape(QFrame.NoFrame)
        self.text_input.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_input.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                color: #ffffff;
                font-size: 13px;
                padding: 6px 10px;
            }
            QTextEdit:focus {
                border-color: #00E5CC;
            }
        """)
        self.text_input.installEventFilter(self)
        outer.addWidget(self.text_input, 1)

        # ── 2. HOLD TO TALK PTT Button ────────────────────────────────────────
        self.ptt_btn = QPushButton("⭕  HOLD TO TALK", self)
        self.ptt_btn.setCursor(Qt.PointingHandCursor)
        self.ptt_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 60, 60, 0.10);
                border: 1.5px solid #ff3c3c;
                border-radius: 10px;
                color: #ff6b6b;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 60, 60, 0.25);
                border-color: #ff5050;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(255, 60, 60, 0.50);
                color: #ffffff;
            }
        """)
        self.ptt_btn.pressed.connect(lambda: self._on_ptt(True))
        self.ptt_btn.released.connect(lambda: self._on_ptt(False))
        outer.addWidget(self.ptt_btn)

        # ── 3. Crisp Action Icons ─────────────────────────────────────────────
        actions_box = QHBoxLayout()
        actions_box.setSpacing(8)

        self.cam_btn = self._make_action_btn("📷", "Camera / Vision mode")
        self.mic_btn = self._make_action_btn("🎤", "Voice input")
        self.tts_btn = self._make_action_btn("🔊", "Text to Speech")

        self.send_btn = QPushButton("➤", self)
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setToolTip("Send message")
        self.send_btn.setFixedSize(36, 36)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton#sendBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00E5CC, stop:1 #009988);
                border: none;
                border-radius: 18px;
                color: #040814;
                font-size: 15px;
                font-weight: 800;
            }
            QPushButton#sendBtn:hover {
                background: #00E5CC;
            }
        """)

        for btn in [self.cam_btn, self.mic_btn, self.tts_btn, self.send_btn]:
            actions_box.addWidget(btn)

        outer.addLayout(actions_box)

        # Connections
        self.send_btn.clicked.connect(self._on_send_clicked)
        self.mic_btn.clicked.connect(self.mic_toggled.emit)
        self.cam_btn.clicked.connect(self.cam_toggled.emit)
        self.tts_btn.clicked.connect(self.tts_toggled.emit)

    def _make_action_btn(self, icon, tooltip):
        btn = QPushButton(icon, self)
        btn.setToolTip(tooltip)
        btn.setFixedSize(36, 36)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 229, 204, 0.06);
                border: 1px solid rgba(0, 229, 204, 0.18);
                border-radius: 18px;
                color: #00E5CC;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: rgba(0, 229, 204, 0.20);
                border-color: #00E5CC;
                color: #ffffff;
            }
        """)
        return btn

    def _on_ptt(self, is_down: bool):
        self.ptt_pressed.emit(is_down)
        if is_down:
            self.mic_toggled.emit()

    def eventFilter(self, obj, event):
        if obj == self.text_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                self._on_send_clicked()
                return True
        return super().eventFilter(obj, event)

    def _on_send_clicked(self):
        text = self.text_input.toPlainText().strip()
        if text:
            self.send_requested.emit(text)
            self.text_input.clear()

    def get_text(self) -> str:
        return self.text_input.toPlainText().strip()

    def set_mic_active(self, active: bool):
        if active:
            self.mic_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 60, 60, 0.25);
                    border: 1.5px solid #ff3c3c;
                    border-radius: 18px;
                    color: #ffffff;
                    font-size: 15px;
                }
            """)
        else:
            self.mic_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 229, 204, 0.06);
                    border: 1px solid rgba(0, 229, 204, 0.18);
                    border-radius: 18px;
                    color: #00E5CC;
                    font-size: 15px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 229, 204, 0.20);
                    border-color: #00E5CC;
                    color: #ffffff;
                }
            """)

    def set_cam_active(self, active: bool):
        pass

    def set_tts_enabled(self, enabled: bool):
        pass

# ── Standalone Preview ────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.setStyleSheet("background-color: #050510;")
    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    input_bar = InputBar()
    layout.addStretch()
    layout.addWidget(input_bar)
    window.resize(900, 70)
    window.show()
    sys.exit(app.exec())
