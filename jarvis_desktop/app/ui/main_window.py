# jarvis_desktop/app/ui/main_window.py

import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QStackedLayout, QApplication
)
from PySide6.QtCore import Qt

from jarvis_desktop.app.ui.header_bar import HeaderBar
from jarvis_desktop.app.ui.sidebar import ActivitySidebar
from jarvis_desktop.app.ui.chat_panel import ChatPanel
from jarvis_desktop.app.ui.command_center import CommandCenter
from jarvis_desktop.app.ui.input_bar import InputBar
from jarvis_desktop.app.ui.settings_dialog import SettingsDialog
from jarvis_desktop.app.ui.orb_widget import OrbWidget

class MainWindow(QMainWindow):
    """
    Main Window container assembling HeaderBar, ActivitySidebar, OrbWidget,
    CommandCenter, ChatPanel, InputBar, and modal SettingsDialog.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("J.A.R.V.I.S — Native Desktop Client")
        self.setMinimumSize(1024, 680)
        self.resize(1280, 800)

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

        # ── 2. Middle Body Splitter (Sidebar + Main Center View) ──────────────
        body_container = QWidget(self.central_widget)
        body_layout = QHBoxLayout(body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left Collapsible Sidebar
        self.sidebar = ActivitySidebar(body_container)
        self.sidebar.hide() # Collapsed by default
        self.sidebar.closed.connect(self.sidebar.hide)
        body_layout.addWidget(self.sidebar)

        # Center Container (Orb Background + Content Overlay)
        center_container = QWidget(body_container)
        center_stacked = QStackedLayout(center_container)
        center_stacked.setStackingMode(QStackedLayout.StackAll)

        # Background Animated Orb
        self.orb_widget = OrbWidget(center_container)
        center_stacked.addWidget(self.orb_widget)

        # Foreground Content Widget
        fg_content = QWidget(center_container)
        fg_layout = QVBoxLayout(fg_content)
        fg_layout.setContentsMargins(20, 16, 20, 16)
        fg_layout.setSpacing(14)

        # Command Center at top of content area
        self.command_center = CommandCenter(fg_content)
        fg_layout.addWidget(self.command_center)

        # Scrollable Chat Stream
        self.chat_panel = ChatPanel(fg_content)
        fg_layout.addWidget(self.chat_panel, 1) # Stretch factor 1

        # Bottom Message Input Bar
        self.input_bar = InputBar(fg_content)
        fg_layout.addWidget(self.input_bar)

        center_stacked.addWidget(fg_content)

        body_layout.addWidget(center_container, 1)
        root_layout.addWidget(body_container, 1)

        # ── 3. Modal Settings Dialog Overlay ──────────────────────────────────
        self.settings_dialog = SettingsDialog(self)

    def toggle_sidebar(self):
        if self.sidebar.isVisible():
            self.sidebar.hide()
        else:
            self.sidebar.show()

    def show_settings(self):
        self.settings_dialog.exec()

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
