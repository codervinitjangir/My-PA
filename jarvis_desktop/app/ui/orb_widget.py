# jarvis_desktop/app/ui/orb_widget.py

import sys
import math
from PySide6.QtWidgets import QWidget, QApplication, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QRadialGradient

class OrbWidget(QWidget):
    """
    Compact J.A.R.V.I.S. HUD Dial Widget — elegant proportioned circular radar dial
    with 72 tick marks, dual rotating arcs (cyan + amber), center text,
    compact status indicator, and model badge without any text overlap.
    """

    CYAN       = QColor(0, 229, 204)        # #00E5CC
    CYAN_DIM   = QColor(0, 229, 204, 50)
    AMBER      = QColor(255, 160, 30)       # Accent arc
    BG_CIRCLE  = QColor(4, 12, 26)         # Dark center core

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._rot         = 0.0          # rotation angle
        self._pulse_angle = 0.0          # pulsing alpha angle
        self._pulse       = 0.0          # 0–1 pulse multiplier

        self._voice_state  = "online"
        self._status_text  = "ONLINE"
        self._status_color = QColor(0, 229, 204)
        self._model_text   = "GEMINI-2.5"

        # ~30 FPS timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_voice_state(self, state: str):
        state_map = {
            "online":    ("ONLINE",     QColor(0,  229, 204)),
            "offline":   ("STANDBY",    QColor(120, 130, 150)),
            "listening": ("LISTENING",  QColor(0,  229, 204)),
            "thinking":  ("PROCESSING", QColor(255, 165,  30)),
            "executing": ("EXECUTING",  QColor(124, 106, 239)),
            "idle":      ("STANDBY",    QColor(120, 130, 150)),
        }
        text, color = state_map.get(state.lower(), ("ONLINE", QColor(0, 229, 204)))
        self._voice_state  = state.lower()
        self._status_text  = text
        self._status_color = color
        self.update()

    def _tick(self):
        speed = 0.6 if self._voice_state in ("listening", "thinking", "executing") else 0.25
        self._rot = (self._rot + speed) % 360.0

        self._pulse_angle += 0.06
        if self._pulse_angle > math.pi * 2:
            self._pulse_angle -= math.pi * 2
        self._pulse = (math.sin(self._pulse_angle) + 1.0) / 2.0

        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        w, h = self.width(), self.height()
        cx = w / 2.0
        dial_cy = h * 0.35

        # Compact proportioned radius — prevents layout overflow
        R = min(w * 0.26, h * 0.24, 130.0)

        # ── 1. Ambient radial glow ──────────────────────────────────────────
        glow = QRadialGradient(QPointF(cx, dial_cy), R * 1.7)
        glow.setColorAt(0.0, QColor(0, 229, 204, int(20 + self._pulse * 15)))
        glow.setColorAt(0.6, QColor(0, 40, 60, int(8 + self._pulse * 6)))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(QPointF(cx, dial_cy), R * 1.7, R * 1.7)

        # ── 2. Dark filled core ─────────────────────────────────────────────
        p.setBrush(QBrush(self.BG_CIRCLE))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, dial_cy), R * 0.82, R * 0.82)

        # ── 3. Radial tick marks (72 ticks) ─────────────────────────────────
        TICK_COUNT = 72
        for i in range(TICK_COUNT):
            ang = math.radians(i * (360.0 / TICK_COUNT) - 90)
            is_major = (i % 6 == 0)
            tick_len  = R * (0.09 if is_major else 0.05)
            tick_from = R * 1.0
            tick_to   = R * 1.0 + tick_len
            alpha = int(190 + self._pulse * 55) if is_major else int(75 + self._pulse * 40)
            pen_w = 1.6 if is_major else 0.8
            p.setPen(QPen(QColor(0, 229, 204, alpha), pen_w))
            x1 = cx   + math.cos(ang) * tick_from
            y1 = dial_cy + math.sin(ang) * tick_from
            x2 = cx   + math.cos(ang) * tick_to
            y2 = dial_cy + math.sin(ang) * tick_to
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # ── 4. Segmented outer ring ─────────────────────────────────────────
        SEG = 40
        full_span = 360.0 / SEG
        gap       = 2.5
        seg_rect  = QRectF(cx - R, dial_cy - R, R * 2, R * 2)
        seg_pen   = QPen(QColor(0, 229, 204, int(110 + self._pulse * 70)), 2.0)
        seg_pen.setCapStyle(Qt.RoundCap)
        p.setPen(seg_pen)
        p.setBrush(Qt.NoBrush)
        for i in range(SEG):
            base = -90.0 + i * full_span + self._rot * 0.22
            start_a = int((base + gap / 2) * 16)
            span_a  = int((full_span - gap) * 16)
            p.drawArc(seg_rect, start_a, span_a)

        # ── 5. Main Rotating Cyan Arc ───────────────────────────────────────
        main_r = R * 0.86
        main_rect = QRectF(cx - main_r, dial_cy - main_r, main_r * 2, main_r * 2)
        main_pen = QPen(QColor(0, 229, 204, 230), 4.0)
        main_pen.setCapStyle(Qt.RoundCap)
        p.setPen(main_pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(main_rect, int((-90.0 + self._rot * 0.35) * 16), int(270 * 16))

        # ── 6. Amber Counter-rotating Arc ──────────────────────────────────
        amber_pen = QPen(QColor(255, 160, 30, 210), 4.0)
        amber_pen.setCapStyle(Qt.RoundCap)
        p.setPen(amber_pen)
        p.drawArc(main_rect, int((-90.0 + 200 + self._rot * 0.35) * 16), int(65 * 16))

        # ── 7. Inner Thin Ring ──────────────────────────────────────────────
        in_r = R * 0.70
        p.setPen(QPen(QColor(0, 229, 204, int(45 + self._pulse * 30)), 0.8))
        p.drawEllipse(QRectF(cx - in_r, dial_cy - in_r, in_r * 2, in_r * 2))

        # ── 8. Center "J.A.R.V.I.S." Text ───────────────────────────────────
        font = QFont("Segoe UI", max(12, int(R * 0.16)), QFont.Weight.Bold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 2.0)
        p.setFont(font)
        p.setPen(QColor(0, 229, 204, int(210 + self._pulse * 45)))
        fm = QFontMetrics(font)
        label = "J.A.R.V.I.S."
        tw = fm.horizontalAdvance(label)
        th = fm.height()
        p.drawText(QPointF(cx - tw / 2, dial_cy + th / 3), label)

        # ── 9. Compact Status Indicator Below Dial ──────────────────────────
        status_y = dial_cy + R + 22
        sfont = QFont("Segoe UI", 10, QFont.Weight.Bold)
        sfont.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        p.setFont(sfont)

        sfm = QFontMetrics(sfont)
        stw = sfm.horizontalAdvance(self._status_text)
        total_w = stw + 14
        start_x = cx - total_w / 2

        # Dot
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self._status_color))
        p.drawEllipse(QPointF(start_x + 4, status_y - 3), 4, 4)

        # Text
        p.setPen(self._status_color)
        p.drawText(QPointF(start_x + 14, status_y), self._status_text)

        # ── 10. Model Badge Below Status (REMOVED) ─────────────────────────

        p.end()


# ── Standalone Preview ────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QWidget()
    window.setStyleSheet("background-color: #050510;")
    layout = QVBoxLayout(window)
    orb = OrbWidget()
    orb.set_voice_state("online")
    layout.addWidget(orb)
    window.resize(400, 400)
    window.setWindowTitle("Compact JARVIS Dial")
    window.show()
    sys.exit(app.exec())
