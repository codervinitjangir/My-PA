# jarvis_desktop/app/ui/chat_panel.py

import sys
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget, QApplication
)
from PySide6.QtCore import Qt, Signal

from jarvis_desktop.app.widgets.chat_bubble import ChatBubble

class ChatPanel(QFrame):
    """
    Main Chat stream container with scrollable message list and interactive Welcome screen with prompt chips.
    """
    chip_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatPanel")
        self.setStyleSheet("background: transparent; border: none;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll Area for Messages
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        
        self.messages_layout = QVBoxLayout(self.scroll_content)
        self.messages_layout.setContentsMargins(20, 20, 20, 20)
        self.messages_layout.setSpacing(16)

        # Welcome Screen Widget
        self.welcome_widget = QWidget(self.scroll_content)
        welcome_layout = QVBoxLayout(self.welcome_widget)
        welcome_layout.setAlignment(Qt.AlignCenter)
        welcome_layout.setSpacing(10)

        welcome_icon = QLabel("🤖", self.welcome_widget)
        welcome_icon.setStyleSheet("font-size: 42px; color: #7c6aef;")
        welcome_icon.setAlignment(Qt.AlignCenter)

        self.welcome_title = QLabel("Good evening.", self.welcome_widget)
        self.welcome_title.setStyleSheet("font-size: 24px; font-weight: 700; color: #ffffff;")
        self.welcome_title.setAlignment(Qt.AlignCenter)

        welcome_sub = QLabel("How may I assist you today?", self.welcome_widget)
        welcome_sub.setStyleSheet("font-size: 14px; color: rgba(255, 255, 255, 0.5);")
        welcome_sub.setAlignment(Qt.AlignCenter)

        # Welcome Chips
        chips_container = QWidget(self.welcome_widget)
        chips_layout = QHBoxLayout(chips_container)
        chips_layout.setSpacing(10)
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
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 16px;
                    color: rgba(255, 255, 255, 0.85);
                    padding: 8px 16px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(124, 106, 239, 0.2);
                    border-color: #7c6aef;
                    color: #ffffff;
                }
            """)
            chip_btn.clicked.connect(lambda checked=False, m=msg: self.chip_clicked.emit(m))
            chips_layout.addWidget(chip_btn)

        welcome_layout.addWidget(welcome_icon)
        welcome_layout.addWidget(self.welcome_title)
        welcome_layout.addWidget(welcome_sub)
        welcome_layout.addWidget(chips_container)

        self.messages_layout.addWidget(self.welcome_widget)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

    def add_user_message(self, text: str):
        if self.welcome_widget.isVisible():
            self.welcome_widget.hide()
        bubble = ChatBubble(text, is_user=True, parent=self.scroll_content)
        # Insert before stretch
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self._scroll_to_bottom()

    def add_assistant_message(self, text: str, latency_info: str = ""):
        if self.welcome_widget.isVisible():
            self.welcome_widget.hide()
        bubble = ChatBubble(text, is_user=False, latency_info=latency_info, parent=self.scroll_content)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self._scroll_to_bottom()

    def clear_messages(self):
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget() and item.widget() != self.welcome_widget:
                item.widget().deleteLater()
        self.welcome_widget.show()

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
    chat_panel.add_user_message("Hello , how are you")
    chat_panel.add_assistant_message("I'm good, just chillin'. You've had a busy day!", latency_info="⚡ STT 734ms • TTFA 7129ms")
    
    layout.addWidget(chat_panel)
    window.resize(700, 500)
    window.setWindowTitle("ChatPanel Preview")
    window.show()
    sys.exit(app.exec())
