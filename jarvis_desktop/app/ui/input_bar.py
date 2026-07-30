# jarvis_desktop/app/ui/input_bar.py

import sys
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QTextEdit, QPushButton, QWidget, QApplication
)
from PySide6.QtCore import Qt, Signal, QEvent

class InputBar(QFrame):
    """
    Bottom message input bar with multiline text editing, camera icon, mic button, TTS button, and send button.
    Matches browser input bar layout 1:1.
    """
    send_requested = Signal(str)
    mic_toggled = Signal()
    cam_toggled = Signal()
    tts_toggled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("inputBar")
        self.setStyleSheet("""
            QFrame#inputBar {
                background-color: rgba(10, 10, 28, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 20px;
                padding: 6px 14px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(10)

        # Text input area
        self.text_input = QTextEdit(self)
        self.text_input.setObjectName("messageInput")
        self.text_input.setPlaceholderText("Ask Jarvis anything...")
        self.text_input.setFixedHeight(36)
        self.text_input.setFrameShape(QFrame.NoFrame)
        self.text_input.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                color: #ffffff;
                font-size: 14px;
                selection-background-color: #7c6aef;
            }
        """)
        self.text_input.installEventFilter(self)
        layout.addWidget(self.text_input, 1)

        # Action Buttons container
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        self.cam_btn = QPushButton("📷", self)
        self.cam_btn.setToolTip("Camera / Vision mode")

        self.mic_btn = QPushButton("🎤", self)
        self.mic_btn.setToolTip("Voice input")

        self.tts_btn = QPushButton("🔊", self)
        self.tts_btn.setToolTip("Text to Speech")

        self.send_btn = QPushButton("✈️", self)
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setToolTip("Send message")

        for btn in [self.cam_btn, self.mic_btn, self.tts_btn]:
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 18px;
                    color: rgba(255, 255, 255, 0.85);
                    font-size: 15px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.12);
                    color: #ffffff;
                }
            """)
            actions_layout.addWidget(btn)

        self.send_btn.setFixedSize(36, 36)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton#sendBtn {
                background-color: #7c6aef;
                border: none;
                border-radius: 18px;
                color: #ffffff;
                font-size: 15px;
            }
            QPushButton#sendBtn:hover {
                background-color: #6956e6;
            }
        """)
        actions_layout.addWidget(self.send_btn)

        layout.addLayout(actions_layout)

        # Connections
        self.send_btn.clicked.connect(self._on_send_clicked)
        self.mic_btn.clicked.connect(self.mic_toggled.emit)
        self.cam_btn.clicked.connect(self.cam_toggled.emit)
        self.tts_btn.clicked.connect(self.tts_toggled.emit)

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

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.setStyleSheet("background-color: #050510;")
    layout = QVBoxLayout(window)
    layout.setContentsMargins(20, 20, 20, 20)
    
    input_bar = InputBar()
    input_bar.send_requested.connect(lambda msg: print(f"Sent: {msg}"))
    
    layout.addStretch()
    layout.addWidget(input_bar)
    window.resize(800, 150)
    window.setWindowTitle("InputBar Preview")
    window.show()
    sys.exit(app.exec())
