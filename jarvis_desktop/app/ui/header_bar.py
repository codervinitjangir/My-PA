# jarvis_desktop/app/ui/header_bar.py

import sys
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget, QApplication
)
from PySide6.QtCore import Qt, Signal

class HeaderBar(QFrame):
    """
    Header Bar component featuring refined typography hierarchy and dynamic multi-state status badge
    (Online, Offline, Listening, Thinking, Executing).
    """
    mode_changed = Signal(str)
    activity_toggled = Signal()
    settings_requested = Signal()
    new_chat_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("headerBar")
        self.setMinimumHeight(76)
        self.setMaximumHeight(76)
        self.setStyleSheet("""
            QFrame#headerBar {
                background-color: rgba(10, 10, 28, 0.72);
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 14, 24, 14)
        layout.setSpacing(20)

        # ── Left: Brand Title & Subtitle Hierarchy ───────────────────────────
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(2)
        
        self.logo_label = QLabel("J.A.R.V.I.S", self)
        self.logo_label.setObjectName("logoLabel")
        self.logo_label.setStyleSheet("font-size: 20px; font-weight: 700; color: #7c6aef; letter-spacing: 1.5px;")

        self.tagline_label = QLabel("Just A Rather Very Intelligent System", self)
        self.tagline_label.setStyleSheet("font-size: 10px; color: rgba(255, 255, 255, 0.40); font-weight: 400;")

        brand_layout.addWidget(self.logo_label)
        brand_layout.addWidget(self.tagline_label)
        layout.addLayout(brand_layout)

        layout.addStretch(1)

        # ── Center: Mode Switcher (Jarvis | General | Realtime) ──────────────
        self.mode_container = QFrame(self)
        self.mode_container.setObjectName("modeSwitcher")
        self.mode_container.setStyleSheet("""
            QFrame#modeSwitcher {
                background-color: rgba(5, 5, 18, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 3px;
            }
        """)
        mode_layout = QHBoxLayout(self.mode_container)
        mode_layout.setContentsMargins(4, 4, 4, 4)
        mode_layout.setSpacing(6)

        self.btn_jarvis = QPushButton("⚡ Jarvis", self.mode_container)
        self.btn_general = QPushButton("💬 General", self.mode_container)
        self.btn_realtime = QPushButton("🌐 Realtime", self.mode_container)

        self.mode_btns = {
            "jarvis": self.btn_jarvis,
            "general": self.btn_general,
            "realtime": self.btn_realtime
        }

        for mode_name, btn in self.mode_btns.items():
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: rgba(255, 255, 255, 0.6);
                    border: none;
                    border-radius: 8px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    color: #ffffff;
                    background-color: rgba(255, 255, 255, 0.08);
                }
            """)
            btn.clicked.connect(lambda checked=False, m=mode_name: self.set_active_mode(m))
            mode_layout.addWidget(btn)

        layout.addWidget(self.mode_container)

        layout.addStretch(1)

        # ── Right: Dynamic Status Badge & Action Icons ───────────────────────
        right_layout = QHBoxLayout()
        right_layout.setSpacing(12)

        # Dynamic Status Badge
        self.status_badge = QFrame(self)
        self.status_badge.setObjectName("statusBadge")
        self.status_badge.setStyleSheet("""
            QFrame#statusBadge {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 4px 12px;
            }
        """)
        status_inner = QHBoxLayout(self.status_badge)
        status_inner.setContentsMargins(6, 2, 8, 2)
        status_inner.setSpacing(6)

        self.status_text = QLabel("● Offline", self.status_badge)
        self.status_text.setStyleSheet("font-size: 12px; font-weight: 600; color: #ff6b6b;")

        status_inner.addWidget(self.status_text)
        right_layout.addWidget(self.status_badge)

        # Action Buttons
        self.activity_btn = QPushButton("📋", self)
        self.activity_btn.setToolTip("View Activity Flow")
        self.settings_btn = QPushButton("⚙️", self)
        self.settings_btn.setToolTip("Settings")
        self.new_chat_btn = QPushButton("➕", self)
        self.new_chat_btn.setToolTip("New Chat")

        for icon_btn in [self.activity_btn, self.settings_btn, self.new_chat_btn]:
            icon_btn.setFixedSize(36, 36)
            icon_btn.setCursor(Qt.PointingHandCursor)
            icon_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 10px;
                    color: #ffffff;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.12);
                    border-color: rgba(124, 106, 239, 0.4);
                }
            """)
            right_layout.addWidget(icon_btn)

        self.activity_btn.clicked.connect(self.activity_toggled.emit)
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        self.new_chat_btn.clicked.connect(self.new_chat_requested.emit)

        layout.addLayout(right_layout)

        self.set_active_mode("jarvis")

    def set_active_mode(self, mode_name: str):
        self._active_mode = mode_name
        for m_name, btn in self.mode_btns.items():
            if m_name == mode_name:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #7c6aef;
                        color: #ffffff;
                        border: none;
                        border-radius: 8px;
                        padding: 6px 14px;
                        font-size: 12px;
                        font-weight: 600;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: rgba(255, 255, 255, 0.6);
                        border: none;
                        border-radius: 8px;
                        padding: 6px 14px;
                        font-size: 12px;
                        font-weight: 500;
                    }
                    QPushButton:hover {
                        color: #ffffff;
                        background-color: rgba(255, 255, 255, 0.08);
                    }
                """)
        self.mode_changed.emit(mode_name)

    def set_system_status(self, status: str):
        """
        Supports states: "online", "offline", "listening", "thinking", "executing"
        """
        status_map = {
            "online": ("● Online", "#51cf66"),
            "offline": ("● Offline", "#ff6b6b"),
            "listening": ("● Listening", "#4ecdc4"),
            "thinking": ("● Thinking", "#fcc419"),
            "executing": ("● Executing", "#7c6aef")
        }
        text, color = status_map.get(status.lower(), ("● " + status.capitalize(), "#ffffff"))
        self.status_text.setText(text)
        self.status_text.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {color};")

    def set_online_status(self, is_online: bool):
        self.set_system_status("online" if is_online else "offline")

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.setStyleSheet("background-color: #050510;")
    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    header = HeaderBar()
    header.set_system_status("listening")
    layout.addWidget(header)
    layout.addStretch()
    window.resize(1000, 100)
    window.show()
    sys.exit(app.exec())
