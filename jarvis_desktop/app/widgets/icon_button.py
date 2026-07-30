# jarvis_desktop/app/widgets/icon_button.py

import sys
from PySide6.QtWidgets import QPushButton, QApplication
from PySide6.QtCore import Qt, QSize

class IconButton(QPushButton):
    """
    Reusable icon action button with rounded border and hover glow effects
    """
    def __init__(self, icon_text="", tooltip="", parent=None, size=36):
        super().__init__(icon_text, parent)
        self.setToolTip(tooltip)
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("headerIconBtn")
        self.setStyleSheet(f"""
            QPushButton#headerIconBtn {{
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: {size // 2 - 2}px;
                color: rgba(255, 255, 255, 0.85);
                font-size: {size // 2.2}px;
            }}
            QPushButton#headerIconBtn:hover {{
                background-color: rgba(255, 255, 255, 0.12);
                border-color: rgba(124, 106, 239, 0.4);
                color: #ffffff;
            }}
            QPushButton#headerIconBtn:pressed {{
                background-color: rgba(124, 106, 239, 0.25);
            }}
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    btn = IconButton("⚙️", "Settings")
    btn.show()
    sys.exit(app.exec())
