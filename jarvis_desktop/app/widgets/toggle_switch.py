# jarvis_desktop/app/widgets/toggle_switch.py

import sys
from PySide6.QtWidgets import QAbstractButton, QApplication
from PySide6.QtCore import Qt, QRectF, QPropertyAnimation, Property, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QPen

class ToggleSwitch(QAbstractButton):
    """
    Modern iOS / macOS style animated toggle switch widget.
    """
    toggled_state = Signal(bool)

    def __init__(self, checked=True, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(44, 24)
        self.setCursor(Qt.PointingHandCursor)

        self._handle_position = 22.0 if checked else 2.0

        self._anim = QPropertyAnimation(self, b"handle_position", self)
        self._anim.setDuration(180)

        self.toggled.connect(self._start_anim)

    def _start_anim(self, checked):
        self._anim.stop()
        self._anim.setEndValue(22.0 if checked else 2.0)
        self._anim.start()
        self.toggled_state.emit(checked)

    def get_handle_position(self):
        return self._handle_position

    def set_handle_position(self, pos):
        self._handle_position = pos
        self.update()

    handle_position = Property(float, get_handle_position, set_handle_position)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        bg_color = QColor("#7c6aef") if self.isChecked() else QColor("rgba(255, 255, 255, 0.15)")

        # Draw pill track background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 12, 12)

        # Draw handle knob circle
        handle_rect = QRectF(self._handle_position, 2.0, 20.0, 20.0)
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawEllipse(handle_rect)

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    toggle = ToggleSwitch(checked=True)
    toggle.show()
    sys.exit(app.exec())
