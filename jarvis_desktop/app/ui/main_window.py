# jarvis_desktop/app/ui/main_window.py

import sys
import math
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedLayout, QLabel, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPen, QColor

from jarvis_desktop.app.ui.header_bar import HeaderBar
from jarvis_desktop.app.ui.sidebar import ActivitySidebar
from jarvis_desktop.app.ui.connectors_panel import ConnectorsPanel
from jarvis_desktop.app.ui.chat_panel import ChatPanel
from jarvis_desktop.app.ui.command_center import CommandCenter
from jarvis_desktop.app.ui.input_bar import InputBar
from jarvis_desktop.app.ui.settings_dialog import SettingsDialog
from jarvis_desktop.app.ui.orb_widget import OrbWidget


# ── Scan-Line Background Widget ───────────────────────────────────────────────
class ScanLineBackground(QWidget):
    """
    Subtle diagonal scan-line texture drawn over the deep space background.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._offset = 0.0
        self._LINE_SPACING = 42
        self._LINE_ANGLE_DEG = 28

        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        self._offset = (self._offset + 0.25) % self._LINE_SPACING
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        pen = QPen(QColor(0, 229, 204, 8))
        pen.setWidth(1)
        painter.setPen(pen)

        w = self.width()
        h = self.height()

        tan_a = math.tan(math.radians(self._LINE_ANGLE_DEG))
        dx_per_dy = tan_a

        start = -w - h
        end = w + h + self._LINE_SPACING
        x_spacing = self._LINE_SPACING / math.cos(math.radians(self._LINE_ANGLE_DEG))

        x = start + self._offset * (x_spacing / self._LINE_SPACING)
        while x < end:
            x1 = int(x)
            y1 = 0
            x2 = int(x - h * dx_per_dy)
            y2 = h
            painter.drawLine(x1, y1, x2, y2)
            x += x_spacing

        painter.end()


# ── Main Window ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    """
    Classified AI 3-Column Tactical Workstation Layout.
    Left Column: Connectors & Modes Panel
    Center Canvas: Interactive J.A.R.V.I.S HUD Dial & Entity Node Counter
    Right Column: Active Chat Session Transcript
    Bottom Row: Tactical Input & Push-To-Talk Control Bar
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("J.A.R.V.I.S — Tactical Workstation")
        self.setMinimumSize(1100, 700)
        self.resize(1340, 840)

        # Root Central Widget
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("rootWindow")
        self.setCentralWidget(self.central_widget)

        root_layout = QVBoxLayout(self.central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── 1. Top Header Bar ────────────────────────────────────────────────
        self.header = HeaderBar(self.central_widget)
        root_layout.addWidget(self.header)

        # ── 2. 3-Column Tactical Workstation Body ─────────────────────────────
        body_container = QWidget(self.central_widget)
        body_layout = QHBoxLayout(body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Activity Sidebar (Collapsible overlay)
        self.sidebar = ActivitySidebar(body_container)
        self.sidebar.hide()
        self.sidebar.closed.connect(self.sidebar.hide)

        # Left Column: Connectors & Modes Panel
        self.connectors_panel = ConnectorsPanel(body_container)
        body_layout.addWidget(self.connectors_panel)

        # Center Column: Orb Canvas & Entity Stats
        center_column = QWidget(body_container)
        center_layout = QVBoxLayout(center_column)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        center_canvas = QWidget(center_column)
        center_stacked = QStackedLayout(center_canvas)
        center_stacked.setStackingMode(QStackedLayout.StackAll)

        # Layer 0: Scan background
        self.scan_bg = ScanLineBackground(center_canvas)
        center_stacked.addWidget(self.scan_bg)

        # Layer 1: J.A.R.V.I.S HUD Dial
        self.orb_widget = OrbWidget(center_canvas)
        center_stacked.addWidget(self.orb_widget)

        # Layer 2: Foreground Content (Command Center + Entity counter)
        fg_content = QWidget(center_canvas)
        fg_layout = QVBoxLayout(fg_content)
        fg_layout.setContentsMargins(16, 12, 16, 12)
        fg_layout.setSpacing(10)

        self.command_center = CommandCenter(fg_content)
        fg_layout.addWidget(self.command_center, 0)

        fg_layout.addStretch(1)

        # Entity node count label (matches screenshot: 1,401 ENTITIES · 3,053 EDGES)
        self.stats_label = QLabel("1,401 ENTITIES  ·  3,053 EDGES", fg_content)
        self.stats_label.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: rgba(0, 229, 204, 0.45); "
            "letter-spacing: 2px; font-family: 'Consolas', monospace;"
        )
        self.stats_label.setAlignment(Qt.AlignCenter)
        fg_layout.addWidget(self.stats_label, 0, Qt.AlignCenter)

        center_stacked.addWidget(fg_content)
        center_layout.addWidget(center_canvas, 1)

        body_layout.addWidget(center_column, 1)

        # Right Column: Active Session Transcript
        self.chat_panel = ChatPanel(body_container)
        self.chat_panel.setFixedWidth(440)
        body_layout.addWidget(self.chat_panel)

        root_layout.addWidget(body_container, 1)

        # ── 3. Bottom Row: Tactical Control & PTT Input Bar ────────────────────
        self.input_bar = InputBar(self.central_widget)
        root_layout.addWidget(self.input_bar, 0)

        # ── 4. Modal Settings Dialog Overlay ─────────────────────────────────
        self.settings_dialog = SettingsDialog(self)

    def toggle_sidebar(self):
        if self.sidebar.isVisible():
            self.sidebar.hide()
        else:
            self.sidebar.show()

    def show_settings(self):
        self.settings_dialog.exec()


# ── Standalone Preview Test ───────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
