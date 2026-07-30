# jarvis_desktop/app/widgets/glass_card.py

import sys
from PySide6.QtWidgets import QFrame, QVBoxLayout, QApplication
from PySide6.QtCore import Qt

class GlassCard(QFrame):
    """
    Reusable glassmorphic panel container with rounded corners and translucent dark styling
    """
    def __init__(self, parent=None, radius=16, border_color="rgba(255, 255, 255, 0.08)", bg_color="rgba(10, 10, 28, 0.72)"):
        super().__init__(parent)
        self.setObjectName("glassPanel")
        self.setStyleSheet(f"""
            QFrame#glassPanel {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: {radius}px;
            }}
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(10)

    def set_content_margins(self, left, top, right, bottom):
        self.layout.setContentsMargins(left, top, right, bottom)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    card = GlassCard()
    card.resize(300, 200)
    card.show()
    sys.exit(app.exec())
