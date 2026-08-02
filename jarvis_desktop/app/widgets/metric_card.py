# jarvis_desktop/app/widgets/metric_card.py

import sys
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QApplication
)
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QRadialGradient, QColor, QBrush


class HUDDot(QWidget):
    """
    Small 10×10 px glowing cyan dot icon — replaces plain emoji icons in the metric rows.
    Briefly flashes when update_metrics() is called (subtle data-update feedback).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._brightness = 0.6          # 0.0 (dim) to 1.0 (full glow)
        self._flashing = False

    def flash(self):
        """Brief glow-up on data update."""
        self._brightness = 1.0
        self._flashing = True
        self.update()
        QTimer.singleShot(350, self._dim_back)

    def _dim_back(self):
        self._brightness = 0.6
        self._flashing = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.width() / 2.0, self.height() / 2.0
        r = 4.0

        # Outer ambient glow
        glow = QRadialGradient(QPointF(cx, cy), r * 2.5)
        glow.setColorAt(0.0, QColor(0, 217, 255, int(60 * self._brightness)))
        glow.setColorAt(1.0, QColor(0, 217, 255, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(cx, cy), r * 2.5, r * 2.5)

        # Core dot
        core = QRadialGradient(QPointF(cx - 0.5, cy - 0.5), r)
        core.setColorAt(0.0, QColor(200, 245, 255, int(240 * self._brightness)))  # White-cyan center
        core.setColorAt(0.5, QColor(0, 217, 255, int(200 * self._brightness)))    # Cyan
        core.setColorAt(1.0, QColor(0, 150, 200, int(80 * self._brightness)))
        painter.setBrush(QBrush(core))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        painter.end()


class MetricCard(QFrame):
    """
    Today's Usage & system metrics card with HUD glow-dot icons.
    Numbers kept as text (not gauges) for fast readability.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setStyleSheet("""
            QFrame#metricCard {
                background-color: rgba(8, 14, 32, 0.78);
                border: 1px solid rgba(0, 217, 255, 0.12);
                border-bottom: 2px solid rgba(0, 217, 255, 0.25);
                border-radius: 16px;
                padding: 14px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title = QLabel("TODAY'S USAGE", self)
        title.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: rgba(0, 217, 255, 0.70); "
            "letter-spacing: 1.5px;"
        )

        self.badge = QLabel("● Low", self)
        self.badge.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #ff6b6b; "
            "background: rgba(255, 107, 107, 0.08); border-radius: 8px; padding: 2px 8px;"
        )

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.badge)
        layout.addLayout(header)

        # Usage Items — HUD dots + name + value
        self.metrics_def = [
            "Dashboard",
            "Morning Brief",
            "Screen Analysis",
            "Resume Session",
            "Browser Opens",
        ]
        self.stat_labels = {}
        self.dot_widgets = {}

        for item_name in self.metrics_def:
            row = QHBoxLayout()
            row.setSpacing(8)

            dot = HUDDot(self)
            self.dot_widgets[item_name] = dot

            label = QLabel(item_name, self)
            label.setStyleSheet(
                "font-size: 13px; color: rgba(255, 255, 255, 0.85); font-weight: 500;"
            )

            val_label = QLabel("0", self)
            val_label.setStyleSheet(
                "font-size: 13px; font-weight: 700; color: #00D9FF;"
            )
            self.stat_labels[item_name] = val_label

            row.addWidget(dot)
            row.addWidget(label)
            row.addStretch()
            row.addWidget(val_label)
            layout.addLayout(row)

    def update_metrics(self, new_stats: dict):
        for name, val in new_stats.items():
            if name in self.stat_labels:
                old_val = self.stat_labels[name].text()
                new_val = str(val)
                if old_val != new_val:
                    self.stat_labels[name].setText(new_val)
                    # Flash the dot on value change
                    if name in self.dot_widgets:
                        self.dot_widgets[name].flash()


# ── Standalone Preview Test ───────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.setStyleSheet("background-color: #050510;")
    layout = QVBoxLayout(window)
    card = MetricCard()
    layout.addWidget(card)
    window.resize(360, 280)
    window.show()
    sys.exit(app.exec())
