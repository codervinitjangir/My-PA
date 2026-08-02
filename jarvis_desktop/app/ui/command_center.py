# jarvis_desktop/app/ui/command_center.py

import sys
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QWidget, QApplication
)
from PySide6.QtCore import Qt, Signal

from jarvis_desktop.app.widgets.metric_card import MetricCard

class CommandCenter(QFrame):
    """
    JARVIS Command Center widget grid with glowing hover effects and smoother border feedback.
    """
    action_triggered = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("commandCenterCard")
        self.setStyleSheet("""
            QFrame#commandCenterCard {
                background-color: rgba(8, 12, 30, 0.80);
                border: 1px solid rgba(0, 217, 255, 0.18);
                border-bottom: 2px solid rgba(0, 217, 255, 0.32);
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        # Header Row with Collapse/Expand Toggle
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        header = QLabel("◈ JARVIS COMMAND CENTER", self)
        header.setObjectName("commandCenterHeader")
        header.setStyleSheet("font-size: 11px; font-weight: 700; color: #00D9FF; letter-spacing: 1.5px;")

        self.toggle_btn = QPushButton("▲ Collapse", self)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(0, 217, 255, 0.45);
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover { color: #00D9FF; }
        """)
        self.toggle_btn.clicked.connect(self.toggle_collapse)

        header_row.addWidget(header)
        header_row.addStretch()
        header_row.addWidget(self.toggle_btn)
        layout.addLayout(header_row)

        # Collapsible Content Body
        self.body_widget = QWidget(self)
        body_layout = QVBoxLayout(self.body_widget)
        body_layout.setContentsMargins(0, 4, 0, 0)
        body_layout.setSpacing(10)

        # Action Buttons Grid (3 columns)
        grid_container = QWidget(self.body_widget)
        grid = QGridLayout(grid_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)

        buttons_def = [
            ("🌅 Morning Brief", "Morning Brief", 0, 0),
            ("▶ Resume Session", "Continue Previous Session", 0, 1),
            ("👁 Analyze Screen", "Analyze Screen", 0, 2),
            ("💻 Open Workspace", "Open VS Code", 1, 0),
            ("🌐 Quick Links", "Quick Links", 1, 1),
            ("📝 Add Friction", "Add Friction", 1, 2),
            ("🔄 Refresh", "Refresh Dashboard", 2, 0)
        ]

        for label_text, action_cmd, row, col in buttons_def:
            btn = QPushButton(label_text, grid_container)
            btn.setObjectName("cmdBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(36)
            btn.setStyleSheet("""
                QPushButton#cmdBtn {
                    background-color: rgba(0, 217, 255, 0.04);
                    border: 1px solid rgba(0, 217, 255, 0.10);
                    border-radius: 8px;
                    color: rgba(255, 255, 255, 0.90);
                    font-size: 12px;
                    font-weight: 500;
                    padding: 6px 10px;
                    text-align: left;
                }
                QPushButton#cmdBtn:hover {
                    background-color: rgba(0, 217, 255, 0.12);
                    border: 1px solid #00D9FF;
                    color: #00D9FF;
                }
                QPushButton#cmdBtn:pressed {
                    background-color: rgba(0, 217, 255, 0.25);
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda checked=False, a=action_cmd: self.action_triggered.emit(a))
            
            if action_cmd == "Refresh Dashboard":
                grid.addWidget(btn, row, col, 1, 3)
            else:
                grid.addWidget(btn, row, col)

        body_layout.addWidget(grid_container)

        # Embedded Metric Card below
        self.metric_card = MetricCard(self.body_widget)
        body_layout.addWidget(self.metric_card)

        layout.addWidget(self.body_widget)

        # Start collapsed by default — user can expand when needed
        self.body_widget.hide()
        self.toggle_btn.setText("▼ Expand")

    def toggle_collapse(self):
        if self.body_widget.isVisible():
            self.body_widget.hide()
            self.toggle_btn.setText("▼ Expand")
        else:
            self.body_widget.show()
            self.toggle_btn.setText("▲ Collapse")

    def set_status(self, text: str):
        """Optional: show live status text in header"""
        pass

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.setStyleSheet("background-color: #050510;")
    layout = QVBoxLayout(window)
    layout.setContentsMargins(20, 20, 20, 20)
    
    cmd_center = CommandCenter()
    cmd_center.action_triggered.connect(lambda action: print(f"Command triggered: {action}"))
    
    layout.addWidget(cmd_center)
    window.resize(550, 480)
    window.setWindowTitle("CommandCenter Preview")
    window.show()
    sys.exit(app.exec())
