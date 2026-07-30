# jarvis_desktop/app/ui/command_center.py

import sys
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QGridLayout, QLabel, QPushButton, QWidget, QApplication
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
                background-color: rgba(12, 12, 32, 0.7);
                border: 1px solid rgba(124, 106, 239, 0.25);
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Header Title
        header = QLabel("JARVIS COMMAND CENTER", self)
        header.setObjectName("commandCenterHeader")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 11px; font-weight: 700; color: #7c6aef; letter-spacing: 1px;")
        layout.addWidget(header)

        # Action Buttons Grid (3 columns)
        grid_container = QWidget(self)
        grid = QGridLayout(grid_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)

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
            btn.setMinimumHeight(42)
            btn.setStyleSheet("""
                QPushButton#cmdBtn {
                    background-color: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.09);
                    border-radius: 10px;
                    color: #ffffff;
                    font-size: 13px;
                    font-weight: 500;
                    padding: 8px 12px;
                }
                QPushButton#cmdBtn:hover {
                    background-color: rgba(124, 106, 239, 0.18);
                    border: 1px solid #7c6aef;
                    color: #ffffff;
                }
                QPushButton#cmdBtn:pressed {
                    background-color: rgba(124, 106, 239, 0.35);
                }
            """)
            btn.clicked.connect(lambda checked=False, a=action_cmd: self.action_triggered.emit(a))
            
            if action_cmd == "Refresh Dashboard":
                grid.addWidget(btn, row, col, 1, 3)
            else:
                grid.addWidget(btn, row, col)

        layout.addWidget(grid_container)

        # Embedded Metric Card below
        self.metric_card = MetricCard(self)
        layout.addWidget(self.metric_card)

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
