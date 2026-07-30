# jarvis_desktop/app/ui/orb_widget.py

import sys
import math
from PySide6.QtWidgets import QWidget, QApplication, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QRadialGradient, QColor, QBrush

class OrbWidget(QWidget):
    """
    Organic Breathing & Pulsing Orb Background (Copilot / Apple Intelligence aesthetic).
    Uses slow sine-wave breathing interpolation instead of rapid rotation.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.angle = 0.0
        self.pulse = 0.0

        # Animation timer (30 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(33)

    def _update_animation(self):
        # Slow organic breathing rate
        self.angle += 0.008
        if self.angle > math.pi * 2:
            self.angle -= math.pi * 2
        # Smooth breathing curve (0.0 to 1.0)
        self.pulse = (math.sin(self.angle) + 1.0) / 2.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        cx = width / 2.0
        cy = height * 0.44

        # Organic breathing radius calculation
        base_radius = min(width, height) * 0.22 + (self.pulse * 12)

        # Ambient Aura Breathing Glow
        grad_outer = QRadialGradient(QPointF(cx, cy), base_radius * 1.7)
        grad_outer.setColorAt(0.0, QColor(124, 106, 239, int(30 + self.pulse * 18)))
        grad_outer.setColorAt(0.55, QColor(78, 205, 196, int(12 + self.pulse * 12)))
        grad_outer.setColorAt(1.0, QColor(5, 5, 16, 0))

        painter.setBrush(QBrush(grad_outer))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy), base_radius * 1.7, base_radius * 1.7)

        # Core Orb
        grad_inner = QRadialGradient(QPointF(cx - base_radius * 0.1, cy - base_radius * 0.1), base_radius)
        grad_inner.setColorAt(0.0, QColor(255, 255, 255, int(130 + self.pulse * 30)))
        grad_inner.setColorAt(0.35, QColor(124, 106, 239, int(150 + self.pulse * 25)))
        grad_inner.setColorAt(0.75, QColor(42, 27, 78, 90))
        grad_inner.setColorAt(1.0, QColor(10, 10, 28, 0))

        painter.setBrush(QBrush(grad_inner))
        painter.drawEllipse(QPointF(cx, cy), base_radius, base_radius)

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.setStyleSheet("background-color: #050510;")
    layout = QVBoxLayout(window)
    orb = OrbWidget()
    layout.addWidget(orb)
    window.resize(600, 600)
    window.setWindowTitle("Organic Breathing Orb Preview")
    window.show()
    sys.exit(app.exec())
