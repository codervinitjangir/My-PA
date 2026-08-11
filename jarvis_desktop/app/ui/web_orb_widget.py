# jarvis_desktop/app/ui/web_orb_widget.py

import json
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget, QLabel, QPushButton, QFrame
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient, QBrush, QFont, QLinearGradient
from PySide6.QtWebEngineCore import QWebEngineSettings


class _OrbPlaceholder(QWidget):
    """
    Premium dark placeholder shown when the Ultron Orb server is not running.
    Features a pulsing animated ring and a clean 'Launch Orb' call-to-action.
    """
    launch_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #05050f;")

        # Pulse animation state
        self._pulse = 0.0
        self._pulse_dir = 1
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)  # ~25 fps — lightweight

        # Centre layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(28)

        # Icon / ring area — purely painted in paintEvent
        self._ring_widget = QWidget(self)
        self._ring_widget.setFixedSize(160, 160)
        self._ring_widget.setAttribute(Qt.WA_TranslucentBackground)
        # Forward paint event so the ring appears inside the layout
        self._ring_widget.paintEvent = self._paint_ring
        layout.addWidget(self._ring_widget, alignment=Qt.AlignHCenter)

        # Title
        title = QLabel("Ultron Orb", self)
        title.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: rgba(124,106,239,0.80);"
            "letter-spacing: 2px; background: transparent;"
        )
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Sub-label
        sub = QLabel("3D Holographic Interface — Not Running", self)
        sub.setStyleSheet(
            "font-size: 12px; color: rgba(255,255,255,0.28); background: transparent;"
        )
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)

        # Launch button
        self.launch_btn = QPushButton("  ◉  Launch Orb", self)
        self.launch_btn.setFixedSize(180, 46)
        self.launch_btn.setCursor(Qt.PointingHandCursor)
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(124,106,239,0.25), stop:1 rgba(0,217,255,0.15));
                border: 1px solid rgba(124,106,239,0.65);
                border-radius: 14px;
                color: #c9b8ff;
                font-size: 14px;
                font-weight: 600;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(124,106,239,0.45), stop:1 rgba(0,217,255,0.30));
                border-color: rgba(124,106,239,0.95);
                color: #ffffff;
            }
            QPushButton:pressed {
                background: rgba(124,106,239,0.55);
            }
        """)
        self.launch_btn.clicked.connect(self.launch_requested.emit)
        layout.addWidget(self.launch_btn, alignment=Qt.AlignHCenter)

        # Hint
        hint = QLabel("Saves ~300 MB RAM when off", self)
        hint.setStyleSheet(
            "font-size: 10px; color: rgba(255,255,255,0.18); background: transparent;"
        )
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

    def _tick(self):
        self._pulse += 0.04 * self._pulse_dir
        if self._pulse >= 1.0:
            self._pulse_dir = -1
        elif self._pulse <= 0.0:
            self._pulse_dir = 1
        self._ring_widget.update()

    def _paint_ring(self, event):
        p = QPainter(self._ring_widget)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = 80, 80
        R = 60

        # Glow
        g = QRadialGradient(cx, cy, R)
        g.setColorAt(0.0, QColor(124, 106, 239, int(30 + self._pulse * 25)))
        g.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(cx - R, cy - R, R * 2, R * 2)

        # Outer dashed ring
        pen = QPen(QColor(124, 106, 239, int(60 + self._pulse * 80)), 1.5, Qt.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(cx - R, cy - R, R * 2, R * 2)

        # Inner ring
        pen2 = QPen(QColor(0, 217, 255, int(40 + self._pulse * 60)), 1.0)
        p.setPen(pen2)
        p.drawEllipse(cx - R + 14, cy - R + 14, (R - 14) * 2, (R - 14) * 2)

        # Centre dot
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(124, 106, 239, int(120 + self._pulse * 100)))
        p.drawEllipse(cx - 6, cy - 6, 12, 12)

        p.end()


class WebOrbWidget(QWidget):
    """
    Wrapper for the Ultron Orb panel.

    - When orb is NOT running: shows a premium dark placeholder with a 'Launch Orb' button.
    - When orb IS running: waits smoothly for Next.js to boot, then fades to the 3D Orb.
    - Features a floating 'Close Orb' button inside the active orb panel.
    """

    # Forwarded signals so the controller can connect
    launch_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack)

        # Page 0 — Placeholder
        self._placeholder = _OrbPlaceholder(self)
        self._placeholder.launch_requested.connect(self.launch_requested.emit)
        self._stack.addWidget(self._placeholder)

        # Page 1 — Live Web View (created lazily on first launch)
        self._web_view: QWebEngineView | None = None
        self._check_boot_timer: QTimer | None = None

        # Floating Close Button (visible only when web view is active)
        self._close_btn = QPushButton("✕ Close Orb", self)
        self._close_btn.setFixedSize(120, 32)
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(124, 106, 239, 0.15);
                border: 1px solid rgba(124, 106, 239, 0.35);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.65);
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(124, 106, 239, 0.40);
                border-color: rgba(124, 106, 239, 0.85);
                color: #ffffff;
            }
        """)
        self._close_btn.clicked.connect(self.close_requested.emit)
        self._close_btn.hide()

        self._voice_state = "online"
        self._stack.setCurrentIndex(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position the close button floating in the top right corner
        self._close_btn.move(self.width() - 140, 20)

    # ── Public API ──────────────────────────────────────────────────────────

    def show_orb(self):
        """Start the smooth boot sequence."""
        self._placeholder.launch_btn.setText("Booting Hologram...")
        self._placeholder.launch_btn.setEnabled(False)

        if self._web_view is None:
            self._web_view = QWebEngineView(self)
            self._web_view.page().setBackgroundColor(QColor(Qt.transparent))
            self._web_view.settings().setAttribute(
                QWebEngineSettings.WebAttribute.WebGLEnabled, True
            )
            self._web_view.settings().setAttribute(
                QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True
            )
            self._web_view.page().featurePermissionRequested.connect(
                self._on_feature_permission
            )
            self._web_view.loadFinished.connect(self._on_load_finished)
            self._stack.addWidget(self._web_view)

        # Start a polling timer to try loading localhost until it actually succeeds
        if self._check_boot_timer is None:
            self._check_boot_timer = QTimer(self)
            self._check_boot_timer.timeout.connect(self._try_load_url)
        
        self._check_boot_timer.start(1000)
        self._try_load_url()

    def _try_load_url(self):
        if self._web_view is not None:
            self._web_view.setUrl(QUrl("http://localhost:3000"))

    def _on_load_finished(self, ok: bool):
        # Only switch the UI if it loaded successfully AND it's our orb url
        if ok and "localhost:3000" in self._web_view.url().toString():
            if self._check_boot_timer:
                self._check_boot_timer.stop()
            
            # Smooth swap — we are ready!
            self._stack.setCurrentWidget(self._web_view)
            self._close_btn.show()
            self._close_btn.raise_()
            
            # Reset placeholder button for next time
            self._placeholder.launch_btn.setText("  ◉  Launch Orb")
            self._placeholder.launch_btn.setEnabled(True)

            # Re-apply current voice state to the new web view
            self.set_voice_state(self._voice_state)

    def hide_orb(self):
        """Immediately switch back to placeholder and kill web view CPU usage."""
        if self._check_boot_timer:
            self._check_boot_timer.stop()

        self._stack.setCurrentWidget(self._placeholder)
        self._close_btn.hide()
        
        self._placeholder.launch_btn.setText("  ◉  Launch Orb")
        self._placeholder.launch_btn.setEnabled(True)

        # Blank the web view to stop it consuming CPU/GPU
        if self._web_view is not None:
            self._web_view.setUrl(QUrl("about:blank"))

    def set_voice_state(self, state: str):
        self._voice_state = state.lower()
        if self._web_view is not None and self._stack.currentWidget() is self._web_view:
            payload = json.dumps({"type": "voice_state", "state": self._voice_state})
            self._web_view.page().runJavaScript(f"window.postMessage({payload}, '*');")

    # ── Private ─────────────────────────────────────────────────────────────

    def _on_feature_permission(self, url, feature):
        from PySide6.QtWebEngineCore import QWebEnginePage
        if feature == QWebEnginePage.Feature.MediaVideoCapture:
            self._web_view.page().setFeaturePermission(
                url, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )

