# jarvis_desktop/app/ui/sidebar.py

import sys
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget, QApplication
)
from PySide6.QtCore import Qt, Signal

class TimelineCard(QFrame):
    """
    Individual activity step routing card matching web flow timeline items
    """
    def __init__(self, step_num: str, step_title: str, step_detail: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("timelineCard")
        self.setStyleSheet("""
            QFrame#timelineCard {
                background-color: rgba(18, 18, 42, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        if step_num:
            num_label = QLabel(str(step_num), self)
            num_label.setStyleSheet("""
                background-color: #2b1f54;
                color: #7c6aef;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: 700;
            """)
            header_layout.addWidget(num_label)

        title_label = QLabel(step_title, self)
        title_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #ececff;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        if step_detail:
            detail_label = QLabel(step_detail, self)
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet("font-size: 11px; color: rgba(255, 255, 255, 0.5); font-family: monospace;")
            layout.addWidget(detail_label)

class ActivitySidebar(QFrame):
    """
    Collapsible Left Activity Panel displaying step-by-step query execution timeline.
    Wider layout (300px) providing clean breathing room for titles.
    """
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarPanel")
        self.setFixedWidth(300) # Widened by 20px
        self.setStyleSheet("""
            QFrame#sidebarPanel {
                background-color: rgba(10, 10, 28, 0.85);
                border-right: 1px solid rgba(255, 255, 255, 0.06);
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 16, 14, 16)
        main_layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title_icon = QLabel("🟣", self)
        title_icon.setStyleSheet("font-size: 14px;")
        title = QLabel("Activity", self)
        title.setObjectName("sidebarTitle")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff;")

        close_btn = QPushButton("✖", self)
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255, 255, 255, 0.5);
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.closed.emit)

        header.addWidget(title_icon)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        main_layout.addLayout(header)

        # Scroll area for activity items
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.items_layout = QVBoxLayout(self.scroll_content)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(10)
        self.items_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # Empty state label
        self.empty_label = QLabel("Send a message to see the flow here.", self.scroll_content)
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet("color: rgba(255, 255, 255, 0.35); font-size: 12px; margin-top: 40px;")
        self.items_layout.insertWidget(0, self.empty_label)

    def add_flow_step(self, step_num: str, step_title: str, step_detail: str = ""):
        if self.empty_label.isVisible():
            self.empty_label.hide()
        card = TimelineCard(step_num, step_title, step_detail, self.scroll_content)
        self.items_layout.insertWidget(self.items_layout.count() - 1, card)

    def clear_flow(self):
        while self.items_layout.count() > 1:
            item = self.items_layout.takeAt(0)
            if item.widget() and item.widget() != self.empty_label:
                item.widget().deleteLater()
        self.empty_label.show()

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.setStyleSheet("background-color: #050510;")
    layout = QHBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    
    sidebar = ActivitySidebar()
    sidebar.add_flow_step("1", "Query detected", "Open YouTube for me")
    
    layout.addWidget(sidebar)
    layout.addStretch()
    window.resize(600, 500)
    window.show()
    sys.exit(app.exec())
