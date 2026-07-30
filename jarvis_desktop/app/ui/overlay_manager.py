# jarvis_desktop/app/ui/overlay_manager.py

import sys
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication

class OverlayManager(QWidget):
    """
    Multi-mode Floating HUD Overlay Manager (Raycast / Copilot style).
    Frameless, translucent, always-on-top pill displaying real-time AI states:
    Listening, Thinking, Speaking, Executing, Done.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedHeight(50)
        self.setMinimumWidth(240)

        # Translucent Container Card
        self.card = QFrame(self)
        self.card.setObjectName("overlayCard")
        self.card.setStyleSheet("""
            QFrame#overlayCard {
                background-color: rgba(10, 10, 28, 0.92);
                border: 1px solid rgba(124, 106, 239, 0.35);
                border-radius: 25px;
            }
        """)

        # Drop shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setYOffset(6)
        self.card.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self.card)
        layout.setContentsMargins(18, 8, 20, 8)
        layout.setSpacing(10)

        self.status_icon = QLabel("🎤", self.card)
        self.status_icon.setStyleSheet("font-size: 16px;")

        self.status_text = QLabel("Listening...", self.card)
        self.status_text.setStyleSheet("font-size: 14px; font-weight: 600; color: #ffffff;")

        layout.addWidget(self.status_icon)
        layout.addWidget(self.status_text)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.card)

        # Cache screen geometry
        self._cached_geom = QGuiApplication.primaryScreen().availableGeometry()

        # Auto-hide Timer
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_hud)

        self._position_top_center()

    def _position_top_center(self):
        screen = self._cached_geom
        x = (screen.width() - self.width()) // 2
        y = screen.top() + 60
        self.move(x, y)

    def show_hud(self, mode: str, text: str = "", auto_hide_ms: int = 3500):
        mode_map = {
            "listening": ("🎤", "Listening...", "rgba(78, 205, 196, 0.4)"),
            "thinking": ("🧠", "Thinking...", "rgba(252, 196, 25, 0.4)"),
            "speaking": ("🔊", "Speaking...", "rgba(124, 106, 239, 0.4)"),
            "executing": ("⚡", text or "Executing action...", "rgba(124, 106, 239, 0.4)"),
            "done": ("✓", text or "Completed", "rgba(81, 207, 102, 0.4)"),
            "error": ("⚠️", text or "Error occurred", "rgba(255, 107, 107, 0.4)")
        }

        icon, default_text, border_color = mode_map.get(mode.lower(), ("ℹ️", text, "rgba(255, 255, 255, 0.2)"))

        self.status_icon.setText(icon)
        self.status_text.setText(text if text else default_text)
        self.card.setStyleSheet(f"""
            QFrame#overlayCard {{
                background-color: rgba(10, 10, 28, 0.92);
                border: 1px solid {border_color};
                border-radius: 25px;
            }}
        """)

        self.adjustSize()
        self._position_top_center()

        self.show()
        if auto_hide_ms > 0:
            self.hide_timer.start(auto_hide_ms)

    def hide_hud(self):
        self.hide()

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    hud = OverlayManager()
    hud.show_hud("executing", "Opening VS Code...")
    sys.exit(app.exec())
