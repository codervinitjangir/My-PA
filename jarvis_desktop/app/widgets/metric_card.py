# jarvis_desktop/app/widgets/metric_card.py

import sys
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QApplication
)
from PySide6.QtCore import Qt

class MetricCard(QFrame):
    """
    Today's Usage & system metrics card component with scan-friendly icons.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setStyleSheet("""
            QFrame#metricCard {
                background-color: rgba(12, 12, 32, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
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
        title.setStyleSheet("font-size: 11px; font-weight: 700; color: rgba(255, 255, 255, 0.6); letter-spacing: 1px;")

        badge = QLabel("● Low", self)
        badge.setStyleSheet("font-size: 11px; font-weight: 600; color: #ff6b6b; background: rgba(255, 107, 107, 0.1); border-radius: 8px; padding: 2px 8px;")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(badge)
        layout.addLayout(header)

        # Usage Items with Icons
        self.metrics_def = [
            ("Dashboard", "📊", "0"),
            ("Morning Brief", "🌅", "0"),
            ("Screen Analysis", "👁", "0"),
            ("Resume Session", "💻", "0"),
            ("Browser Opens", "🌐", "0")
        ]
        self.stat_labels = {}

        for item_name, icon, default_val in self.metrics_def:
            row = QHBoxLayout()
            row.setSpacing(8)

            icon_lbl = QLabel(icon, self)
            icon_lbl.setStyleSheet("font-size: 13px;")

            label = QLabel(item_name, self)
            label.setStyleSheet("font-size: 13px; color: rgba(255, 255, 255, 0.85); font-weight: 500;")
            
            val_label = QLabel(default_val, self)
            val_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff;")
            self.stat_labels[item_name] = val_label

            row.addWidget(icon_lbl)
            row.addWidget(label)
            row.addStretch()
            row.addWidget(val_label)
            layout.addLayout(row)

    def update_metrics(self, new_stats: dict):
        for name, val in new_stats.items():
            if name in self.stat_labels:
                self.stat_labels[name].setText(str(val))

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.setStyleSheet("background-color: #050510;")
    layout = QVBoxLayout(window)
    card = MetricCard()
    layout.addWidget(card)
    window.resize(360, 260)
    window.show()
    sys.exit(app.exec())
