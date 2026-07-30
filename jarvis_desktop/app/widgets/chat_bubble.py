# jarvis_desktop/app/widgets/chat_bubble.py

import sys
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QApplication
)
from PySide6.QtCore import Qt

class ChatBubble(QWidget):
    """
    Chat message bubble widget supporting User and Assistant layouts,
    avatars, timestamps, streaming token append, copy button, and formatted text rendering.
    """
    def __init__(self, text: str = "", is_user: bool = False, sender_name: str = "Jarvis (Jarvis)", latency_info: str = "", parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.raw_text = text

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 4, 10, 4)
        main_layout.setSpacing(10)

        # Bubble Container Frame
        self.card = QFrame(self)
        self.card.setObjectName("chatBubbleCard")
        
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(4)

        if not is_user:
            # Assistant Label Header with Copy Button
            header_row = QHBoxLayout()
            name_label = QLabel(sender_name, self.card)
            name_label.setStyleSheet("font-size: 11px; color: rgba(255, 255, 255, 0.5); font-weight: 500;")

            copy_btn = QPushButton("📋 Copy", self.card)
            copy_btn.setCursor(Qt.PointingHandCursor)
            copy_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: rgba(255, 255, 255, 0.4);
                    font-size: 10px;
                }
                QPushButton:hover { color: #7c6aef; }
            """)
            copy_btn.clicked.connect(self.copy_to_clipboard)

            header_row.addWidget(name_label)
            header_row.addStretch()
            header_row.addWidget(copy_btn)
            card_layout.addLayout(header_row)

        # Message Text Label
        self.text_label = QLabel(text, self.card)
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        if is_user:
            self.card.setStyleSheet("""
                QFrame#chatBubbleCard {
                    background-color: #2a1b4e;
                    border: 1px solid #483285;
                    border-radius: 16px;
                }
            """)
            self.text_label.setStyleSheet("font-size: 14px; color: #ffffff;")
        else:
            self.card.setStyleSheet("""
                QFrame#chatBubbleCard {
                    background-color: rgba(18, 18, 42, 0.85);
                    border: 1px solid rgba(124, 106, 239, 0.18);
                    border-radius: 16px;
                }
            """)
            self.text_label.setStyleSheet("font-size: 14px; color: rgba(255, 255, 255, 0.93);")

        card_layout.addWidget(self.text_label)

        if latency_info:
            self.latency_label = QLabel(latency_info, self.card)
            self.latency_label.setStyleSheet("font-size: 10px; color: #4ecdc4; font-family: monospace; margin-top: 4px;")
            card_layout.addWidget(self.latency_label)

        # Avatars
        avatar = QLabel("👤" if is_user else "🤖", self)
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            font-size: 16px;
        """)

        if is_user:
            main_layout.addStretch()
            main_layout.addWidget(self.card)
            main_layout.addWidget(avatar)
        else:
            main_layout.addWidget(avatar)
            main_layout.addWidget(self.card)
            main_layout.addStretch()

    def append_chunk(self, chunk: str):
        """Append streaming token chunk dynamically"""
        self.raw_text += chunk
        self.text_label.setText(self.raw_text)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.raw_text)

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.setStyleSheet("background-color: #050510;")
    layout = QVBoxLayout(window)
    
    b1 = ChatBubble("Open YouTube for me", is_user=True)
    b2 = ChatBubble("I've opened YouTube for you.", is_user=False, latency_info="⚡ STT 734ms • TTFA 7129ms")
    
    layout.addWidget(b1)
    layout.addWidget(b2)
    layout.addStretch()
    
    window.resize(600, 300)
    window.show()
    sys.exit(app.exec())
