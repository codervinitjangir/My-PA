# jarvis_desktop/app/ui/settings_dialog.py

import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget, QApplication
)
from PySide6.QtCore import Qt, Signal

from jarvis_desktop.app.widgets.toggle_switch import ToggleSwitch

class SettingsDialog(QDialog):
    """
    Modal Settings popup dialog matching screenshot 2 1:1.
    """
    setting_changed = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsDialog")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 360)

        # Translucent Container Card
        card = QFrame(self)
        card.setObjectName("settingsContainer")
        card.setStyleSheet("""
            QFrame#settingsContainer {
                background-color: #0b0b1f;
                border: 1px solid rgba(124, 106, 239, 0.3);
                border-radius: 20px;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("Settings", card)
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #ffffff;")

        close_btn = QPushButton("✖", card)
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
                color: rgba(255, 255, 255, 0.7);
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.accept)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        card_layout.addLayout(header)

        # Settings Toggle List
        self.toggles_def = [
            ("auto_activity", "Auto-open activity panel", True),
            ("auto_search", "Auto-open search results", True),
            ("thinking_sounds", "Thinking sound effects", True),
            ("voice_interrupt", "Voice interruption", True)
        ]
        self.switches = {}

        for key, label_text, default_val in self.toggles_def:
            row = QHBoxLayout()
            lbl = QLabel(label_text, card)
            lbl.setStyleSheet("font-size: 13px; color: rgba(255, 255, 255, 0.9); font-weight: 500;")

            switch = ToggleSwitch(checked=default_val, parent=card)
            switch.toggled_state.connect(lambda state, k=key: self.setting_changed.emit(k, state))
            self.switches[key] = switch

            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(switch)
            card_layout.addLayout(row)

        # Bottom Hint Description
        hint = QLabel(
            "Activity and search panels open automatically when data is available. "
            "Thinking sounds play a short cue while the AI processes. "
            "Voice interruption lets you interrupt the AI by speaking — it will stop talking and listen to you.",
            card
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; color: rgba(255, 255, 255, 0.45); line-height: 1.4;")
        card_layout.addWidget(hint)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(card)

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = SettingsDialog()
    dialog.setting_changed.connect(lambda k, v: print(f"Setting {k} changed to {v}"))
    dialog.show()
    sys.exit(app.exec())
