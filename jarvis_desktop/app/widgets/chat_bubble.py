# jarvis_desktop/app/widgets/chat_bubble.py

import sys
import datetime
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QApplication, QSizePolicy
)
from PySide6.QtCore import Qt

class ChatBubble(QWidget):
    """
    Chat transcript message row for Classified AI workstation layout.
    Displays timestamp (HH:MM:SS), sender name / TOOL badge, formatted text, and latency info.
    """
    def __init__(self, text: str = "", is_user: bool = False, sender_name: str = "JARVIS", timestamp: str = "", is_tool: bool = False, tool_name: str = "", latency_info: str = "", parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.is_tool = is_tool
        self.raw_text = text

        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 4, 6, 4)
        main_layout.setSpacing(10)

        # ── 1. Timestamp Label (HH:MM:SS) ──────────────────────────────────────
        ts_label = QLabel(timestamp, self)
        ts_label.setFixedWidth(58)
        ts_label.setStyleSheet("font-size: 11px; font-family: 'Consolas', monospace; color: rgba(255, 255, 255, 0.35);")
        main_layout.addWidget(ts_label, 0, Qt.AlignTop)

        # ── 2. Sender / Tool Badge ─────────────────────────────────────────────
        if is_tool:
            badge_frame = QFrame(self)
            badge_layout = QHBoxLayout(badge_frame)
            badge_layout.setContentsMargins(6, 2, 8, 2)
            badge_layout.setSpacing(4)
            badge_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(0, 229, 204, 0.08);
                    border: 1px solid rgba(0, 229, 204, 0.25);
                    border-radius: 4px;
                }
            """)
            t_title = QLabel("TOOL", badge_frame)
            t_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #00E5CC;")
            t_dot = QLabel("●", badge_frame)
            t_dot.setStyleSheet("font-size: 8px; color: #00E5CC;")
            t_name = QLabel(tool_name or "execute", badge_frame)
            t_name.setStyleSheet("font-size: 10px; font-family: 'Consolas', monospace; color: rgba(255, 255, 255, 0.9);")
            badge_layout.addWidget(t_title)
            badge_layout.addWidget(t_dot)
            badge_layout.addWidget(t_name)
            main_layout.addWidget(badge_frame, 0, Qt.AlignTop)
        else:
            sender_lbl = QLabel("YOU" if is_user else "JARVIS", self)
            sender_lbl.setFixedWidth(52)
            sender_color = "#00E5CC" if not is_user else "rgba(255, 255, 255, 0.65)"
            sender_lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {sender_color}; letter-spacing: 0.5px;")
            main_layout.addWidget(sender_lbl, 0, Qt.AlignTop)

        # ── 3. Content Label ──────────────────────────────────────────────────
        content_box = QVBoxLayout()
        content_box.setContentsMargins(0, 0, 0, 0)
        content_box.setSpacing(2)

        self.text_label = QLabel(text, self)
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.text_label.setStyleSheet("font-size: 13px; color: rgba(255, 255, 255, 0.92); line-height: 1.4;")
        content_box.addWidget(self.text_label)

        if latency_info:
            lat_lbl = QLabel(latency_info, self)
            lat_lbl.setStyleSheet("font-size: 10px; font-family: 'Consolas', monospace; color: rgba(0, 229, 204, 0.55);")
            content_box.addWidget(lat_lbl)

        main_layout.addLayout(content_box, 1)

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
    
    b1 = ChatBubble("Online, sir. Try me.", is_user=False, timestamp="23:14:21")
    b2 = ChatBubble("Text my girlfriend that I miss you.", is_user=True, timestamp="23:15:26")
    b3 = ChatBubble("Text sent to Kayla: I miss you. It's queued for delivery.", is_tool=True, tool_name="send_sms", timestamp="23:15:27")
    b4 = ChatBubble("All systems optimal, sir. Ready to tackle whatever's on your mind.", is_user=False, timestamp="23:15:29")
    
    for b in [b1, b2, b3, b4]:
        layout.addWidget(b)
    layout.addStretch()
    
    window.resize(600, 300)
    window.show()
    sys.exit(app.exec())
