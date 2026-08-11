# jarvis_desktop/app/ui/header_bar.py

import sys
import math
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QPen, QColor


# ── HUD Animated Status Ring ──────────────────────────────────────────────────
class HUDStatusRing(QWidget):
    """
    Thin animated arc ring that rotates when Jarvis is active (listening/thinking/executing).
    Static dimmed circle when idle/online/offline.
    Supplementary to the text label — never replaces it.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._start_angle = 0          # Current rotation angle (degrees × 16 for Qt)
        self._ring_color = QColor(80, 80, 80, 80)   # Default: dim gray
        self._is_animated = False
        self._arc_span = 270 * 16      # Arc spans 270° of the circle

        # Rotation timer
        self._timer = QTimer(self)
        self._timer.setInterval(20)    # ~50 FPS rotation
        self._timer.timeout.connect(self._tick)

    def _tick(self):
        self._start_angle = (self._start_angle + 48) % (360 * 16)   # ~2s full rotation
        self.update()

    def set_state(self, status: str):
        state_map = {
            "online":     (QColor(81, 207, 102, 180), False),     # Green, static
            "offline":    (QColor(255, 107, 107, 120), False),    # Red dim, static
            "listening":  (QColor(0, 217, 255, 220), True),       # Cyan, animated
            "thinking":   (QColor(252, 196, 25, 200), True),      # Amber, animated
            "executing":  (QColor(124, 106, 239, 220), True),     # Purple, animated
        }
        color, animated = state_map.get(status.lower(), (QColor(255, 255, 255, 80), False))
        self._ring_color = color
        self._is_animated = animated

        if animated and not self._timer.isActive():
            self._timer.start()
        elif not animated:
            self._timer.stop()
            self._start_angle = 90 * 16   # Reset to top

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen(self._ring_color, 2.0)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        margin = 2
        rect = self.rect().adjusted(margin, margin, -margin, -margin)

        if self._is_animated:
            painter.drawArc(rect, self._start_angle, self._arc_span)
        else:
            # Static full circle at dim opacity
            painter.drawEllipse(rect)

        painter.end()


# ── Header Bar ────────────────────────────────────────────────────────────────
class HeaderBar(QFrame):
    """
    Header Bar component featuring refined typography hierarchy and dynamic multi-state status badge
    (Online, Offline, Listening, Thinking, Executing) with a HUD animated arc ring indicator.
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
                background-color: rgba(8, 12, 28, 0.92);
                border-bottom: 1px solid rgba(0, 217, 255, 0.22);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 14, 24, 14)
        layout.setSpacing(20)

        # ── Left: Brand Title & Subtitle Hierarchy ────────────────────────────
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(2)
        
        self.logo_label = QLabel("J.A.R.V.I.S", self)
        self.logo_label.setObjectName("logoLabel")
        self.logo_label.setStyleSheet(
            "font-size: 20px; font-weight: 700; color: #00D9FF; letter-spacing: 2px;"
        )

        self.tagline_label = QLabel("Just A Rather Very Intelligent System", self)
        self.tagline_label.setStyleSheet(
            "font-size: 10px; color: rgba(0, 217, 255, 0.35); font-weight: 400; letter-spacing: 0.5px;"
        )

        brand_layout.addWidget(self.logo_label)
        brand_layout.addWidget(self.tagline_label)
        layout.addLayout(brand_layout)

        layout.addStretch(1)

        # ── Center: Mode Switcher (Jarvis | General | Realtime) ──────────────
        self.mode_container = QFrame(self)
        self.mode_container.setObjectName("modeSwitcher")
        self.mode_container.setStyleSheet("""
            QFrame#modeSwitcher {
                background-color: rgba(5, 5, 18, 0.90);
                border: 1px solid rgba(0, 217, 255, 0.12);
                border-radius: 12px;
                padding: 3px;
            }
        """)
        mode_layout = QHBoxLayout(self.mode_container)
        mode_layout.setContentsMargins(4, 4, 4, 4)
        mode_layout.setSpacing(6)

        self.btn_jarvis = QPushButton("◈ Jarvis", self.mode_container)
        self.btn_general = QPushButton("▤ General", self.mode_container)
        self.btn_realtime = QPushButton("◎ Realtime", self.mode_container)

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
                    color: #00D9FF;
                    background-color: rgba(0, 217, 255, 0.07);
                }
            """)
            btn.clicked.connect(lambda checked=False, m=mode_name: self.set_active_mode(m))
            mode_layout.addWidget(btn)

        layout.addWidget(self.mode_container)

        layout.addStretch(1)

        # ── Right: Dynamic Status Badge & Action Icons ────────────────────────
        right_layout = QHBoxLayout()
        right_layout.setSpacing(12)

        # Dynamic Status Badge with animated ring
        self.status_badge = QFrame(self)
        self.status_badge.setObjectName("statusBadge")
        self.status_badge.setStyleSheet("""
            QFrame#statusBadge {
                background-color: rgba(0, 217, 255, 0.04);
                border: 1px solid rgba(0, 217, 255, 0.14);
                border-radius: 14px;
                padding: 4px 12px;
            }
        """)
        status_inner = QHBoxLayout(self.status_badge)
        status_inner.setContentsMargins(6, 2, 8, 2)
        status_inner.setSpacing(6)

        # HUD animated ring — supplementary to text
        self.status_ring = HUDStatusRing(self.status_badge)
        status_inner.addWidget(self.status_ring)

        self.status_text = QLabel("● Offline", self.status_badge)
        self.status_text.setStyleSheet("font-size: 12px; font-weight: 600; color: #ff6b6b;")

        status_inner.addWidget(self.status_text)
        right_layout.addWidget(self.status_badge)

        # Action Buttons
        self.activity_btn = QPushButton("≡", self)
        self.activity_btn.setToolTip("View Activity Flow")
        self.settings_btn = QPushButton("⛭", self)
        self.settings_btn.setToolTip("Settings")
        self.new_chat_btn = QPushButton("＋", self)
        self.new_chat_btn.setToolTip("New Chat")

        for icon_btn in [self.activity_btn, self.settings_btn, self.new_chat_btn]:
            icon_btn.setFixedSize(36, 36)
            icon_btn.setCursor(Qt.PointingHandCursor)
            icon_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 217, 255, 0.04);
                    border: 1px solid rgba(0, 217, 255, 0.10);
                    border-radius: 10px;
                    color: rgba(255, 255, 255, 0.80);
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 217, 255, 0.12);
                    border-color: rgba(0, 217, 255, 0.45);
                    color: #00D9FF;
                }
            """)
            right_layout.addWidget(icon_btn)

        self.activity_btn.clicked.connect(self.activity_toggled.emit)
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        self.new_chat_btn.clicked.connect(self.new_chat_requested.emit)

        layout.addLayout(right_layout)

        self.set_active_mode("jarvis")
        self.set_system_status("offline")

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
                        color: #00D9FF;
                        background-color: rgba(0, 217, 255, 0.07);
                    }
                """)
        self.mode_changed.emit(mode_name)

    def set_system_status(self, status: str):
        """
        Supports states: "online", "offline", "listening", "thinking", "executing"
        Updates both the text label and the animated HUD ring.
        """
        status_map = {
            "online":    ("● Online",    "#51cf66"),
            "offline":   ("● Offline",   "#ff6b6b"),
            "listening": ("● Listening", "#00D9FF"),
            "thinking":  ("● Thinking",  "#fcc419"),
            "executing": ("● Executing", "#7c6aef"),
        }
        text, color = status_map.get(status.lower(), ("● " + status.capitalize(), "#ffffff"))
        self.status_text.setText(text)
        self.status_text.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {color};")
        self.status_ring.set_state(status.lower())

    def set_online_status(self, is_online: bool):
        self.set_system_status("online" if is_online else "offline")

# ── Standalone Preview Test ───────────────────────────────────────────────────
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
    import sys
    sys.exit(app.exec())
