# jarvis_desktop/app/ui/chat_panel.py

import sys
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget, QApplication
)
from PySide6.QtCore import Qt, Signal

from jarvis_desktop.app.widgets.chat_bubble import ChatBubble

class ChatPanel(QFrame):
    """
    Transcript session panel for Classified AI workstation layout.
    Features header session toolbar (SESSION - GENERAL, Search, Settings, Clear)
    and clean scrollable message stream with timestamps & tool execution badges.
    """
    chip_clicked = Signal(str)
    clear_requested = Signal()
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatPanel")
        self.setStyleSheet("""
            QFrame#chatPanel {
                background-color: rgba(6, 10, 22, 0.92);
                border-left: 1px solid rgba(0, 217, 255, 0.12);
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 1. Session Top Header Bar ─────────────────────────────────────────
        session_header = QFrame(self)
        session_header.setStyleSheet("""
            QFrame {
                background-color: rgba(4, 8, 18, 0.95);
                border-bottom: 1px solid rgba(0, 217, 255, 0.12);
                padding: 6px 12px;
            }
        """)
        h_layout = QHBoxLayout(session_header)
        h_layout.setContentsMargins(10, 6, 10, 6)
        h_layout.setSpacing(8)

        s_title = QLabel("SESSION - GENERAL", session_header)
        s_title.setStyleSheet("font-size: 10px; font-weight: 700; color: rgba(255, 255, 255, 0.4); letter-spacing: 1.2px;")
        h_layout.addWidget(s_title)

        h_layout.addStretch()

        self.btn_search = QPushButton("🔍 SEARCH", session_header)
        self.btn_settings = QPushButton("⚙ SETTINGS", session_header)
        self.btn_clear = QPushButton("🗑 CLEAR", session_header)

        for btn in [self.btn_search, self.btn_settings, self.btn_clear]:
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 6px;
                    color: rgba(255, 255, 255, 0.7);
                    font-size: 10px;
                    font-weight: 600;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 229, 204, 0.12);
                    border-color: #00E5CC;
                    color: #00E5CC;
                }
            """)
            h_layout.addWidget(btn)

        self.btn_clear.clicked.connect(self.clear_messages)
        self.btn_settings.clicked.connect(self.settings_requested.emit)

        main_layout.addWidget(session_header)

        # ── 2. Scroll Area for Message Transcript ────────────────────────────
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        
        self.messages_layout = QVBoxLayout(self.scroll_content)
        self.messages_layout.setContentsMargins(12, 12, 12, 12)
        self.messages_layout.setSpacing(10)

        # Welcome Prompt Chips Widget (visible when empty)
        self.welcome_widget = QWidget(self.scroll_content)
        welcome_layout = QVBoxLayout(self.welcome_widget)
        welcome_layout.setAlignment(Qt.AlignCenter)
        welcome_layout.setSpacing(8)

        welcome_title = QLabel("JARVIS WORKSTATION ACTIVE", self.welcome_widget)
        welcome_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #00E5CC; letter-spacing: 1.5px;")
        welcome_sub = QLabel("Select a quick prompt or type a command to begin:", self.welcome_widget)
        welcome_sub.setStyleSheet("font-size: 11px; color: rgba(255, 255, 255, 0.4);")

        chips_container = QWidget(self.welcome_widget)
        chips_layout = QHBoxLayout(chips_container)
        chips_layout.setSpacing(6)
        chips_layout.setAlignment(Qt.AlignCenter)

        chip_prompts = [
            ("What can you do?", "What can you do?"),
            ("Open YouTube", "Open YouTube for me"),
            ("Fun fact", "Tell me a fun fact"),
            ("Play music", "Play some music")
        ]

        for label, msg in chip_prompts:
            chip_btn = QPushButton(label, chips_container)
            chip_btn.setCursor(Qt.PointingHandCursor)
            chip_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 229, 204, 0.05);
                    border: 1px solid rgba(0, 229, 204, 0.18);
                    border-radius: 12px;
                    color: rgba(255, 255, 255, 0.80);
                    padding: 6px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 229, 204, 0.15);
                    border-color: #00E5CC;
                    color: #00E5CC;
                }
            """)
            chip_btn.clicked.connect(lambda checked=False, m=msg: self.chip_clicked.emit(m))
            chips_layout.addWidget(chip_btn)

        welcome_layout.addWidget(welcome_title, 0, Qt.AlignCenter)
        welcome_layout.addWidget(welcome_sub, 0, Qt.AlignCenter)
        welcome_layout.addWidget(chips_container)

        self.messages_layout.addWidget(self.welcome_widget)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

    def add_user_message(self, text: str, timestamp: str = ""):
        if self.welcome_widget.isVisible():
            self.welcome_widget.hide()
        bubble = ChatBubble(text, is_user=True, timestamp=timestamp, parent=self.scroll_content)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self._scroll_to_bottom()

    def add_assistant_message(self, text: str, latency_info: str = "", timestamp: str = ""):
        if self.welcome_widget.isVisible():
            self.welcome_widget.hide()
        bubble = ChatBubble(text, is_user=False, latency_info=latency_info, timestamp=timestamp, parent=self.scroll_content)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self._scroll_to_bottom()
        return bubble

    def add_tool_message(self, text: str, tool_name: str = "", timestamp: str = ""):
        if self.welcome_widget.isVisible():
            self.welcome_widget.hide()
        bubble = ChatBubble(text, is_tool=True, tool_name=tool_name, timestamp=timestamp, parent=self.scroll_content)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self._scroll_to_bottom()

    def clear_messages(self):
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget() and item.widget() != self.welcome_widget:
                item.widget().deleteLater()
        self.welcome_widget.show()
        self.clear_requested.emit()

    def _scroll_to_bottom(self):
        QApplication.processEvents()
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.setStyleSheet("background-color: #050510;")
    layout = QVBoxLayout(window)
    
    chat_panel = ChatPanel()
    chat_panel.add_assistant_message("Online, sir. Try me.", timestamp="23:14:21")
    chat_panel.add_user_message("Text my girlfriend that I miss you.", timestamp="23:15:26")
    chat_panel.add_tool_message("Text sent to Kayla: I miss you.", tool_name="send_sms", timestamp="23:15:27")
    chat_panel.add_assistant_message("All systems optimal, sir.", timestamp="23:15:29")
    
    layout.addWidget(chat_panel)
    window.resize(450, 550)
    window.setWindowTitle("ChatPanel Tactical Preview")
    window.show()
    sys.exit(app.exec())
