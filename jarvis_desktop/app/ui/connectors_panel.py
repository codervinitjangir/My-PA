# jarvis_desktop/app/ui/connectors_panel.py

import sys
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QApplication, QScrollArea
)
from PySide6.QtCore import Qt, Signal

class ConnectorsPanel(QFrame):
    """
    Left-hand tactical sidebar for Classified AI workstation layout.
    Displays Workspace Streams, Modes (Voice/Text/Auto), and Connectors status.
    """
    mode_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("connectorsPanel")
        self.setFixedWidth(220)
        self.setStyleSheet("""
            QFrame#connectorsPanel {
                background-color: rgba(6, 10, 22, 0.95);
                border-right: 1px solid rgba(0, 217, 255, 0.12);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(18)

        # ── 1. STREAMS Section ────────────────────────────────────────────────
        streams_header = QLabel("WORKSPACE STREAMS", self)
        streams_header.setStyleSheet("font-size: 10px; font-weight: 700; color: rgba(255, 255, 255, 0.4); letter-spacing: 1.2px;")
        layout.addWidget(streams_header)

        streams_box = QVBoxLayout()
        streams_box.setSpacing(6)
        for stream_name, time_ago in [("● General", "1h"), ("BrainDump", "63d"), ("Research", "75d")]:
            row = QHBoxLayout()
            lbl = QLabel(stream_name, self)
            is_active = stream_name.startswith("●")
            color = "#00E5CC" if is_active else "rgba(255, 255, 255, 0.6)"
            lbl.setStyleSheet(f"font-size: 12px; font-weight: {'700' if is_active else '500'}; color: {color};")
            time_lbl = QLabel(time_ago, self)
            time_lbl.setStyleSheet("font-size: 10px; color: rgba(255, 255, 255, 0.3);")
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(time_lbl)
            streams_box.addLayout(row)
        layout.addLayout(streams_box)

        # ── 2. MODES Section ──────────────────────────────────────────────────
        modes_header = QLabel("MODES", self)
        modes_header.setStyleSheet("font-size: 10px; font-weight: 700; color: rgba(255, 255, 255, 0.4); letter-spacing: 1.2px;")
        layout.addWidget(modes_header)

        self.mode_btns = {}
        modes_data = [
            ("Voice", "HANDS-FREE ORB", "voice"),
            ("Text", "CHAT-STYLE TYPING", "text"),
            ("Auto", "AMBIENT ALERTS ONLY", "auto")
        ]
        for name, sub, key in modes_data:
            btn = QPushButton(self)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(44)
            btn_layout = QVBoxLayout(btn)
            btn_layout.setContentsMargins(10, 5, 10, 5)
            btn_layout.setSpacing(1)
            
            t_lbl = QLabel(f"● {name}" if key == "voice" else name, btn)
            t_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #ffffff;")
            s_lbl = QLabel(sub, btn)
            s_lbl.setStyleSheet("font-size: 9px; color: rgba(255, 255, 255, 0.4);")
            
            btn_layout.addWidget(t_lbl)
            btn_layout.addWidget(s_lbl)
            
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: rgba(0, 229, 204, 0.12);
                    border-color: #00E5CC;
                }
            """)
            btn.clicked.connect(lambda checked=False, k=key: self._on_mode_click(k))
            self.mode_btns[key] = btn
            layout.addWidget(btn)

        # ── 3. CONNECTORS Section ─────────────────────────────────────────────
        conn_header_row = QHBoxLayout()
        conn_header = QLabel("CONNECTORS", self)
        conn_header.setStyleSheet("font-size: 10px; font-weight: 700; color: rgba(255, 255, 255, 0.4); letter-spacing: 1.2px;")
        conn_count = QLabel("7/8", self)
        conn_count.setStyleSheet("font-size: 10px; font-weight: 700; color: #00E5CC;")
        conn_header_row.addWidget(conn_header)
        conn_header_row.addStretch()
        conn_header_row.addWidget(conn_count)
        layout.addLayout(conn_header_row)

        connectors = [
            ("BETINT", "OK"),
            ("Gmail", "OK"),
            ("Calendar", "OK"),
            ("Drive", "OK"),
            ("Notion", "OK"),
            ("Health", "OK"),
            ("Memory", "OFF"),
            ("Slack", "OK")
        ]

        conn_scroll = QScrollArea(self)
        conn_scroll.setWidgetResizable(True)
        conn_scroll.setFrameShape(QFrame.NoFrame)
        conn_scroll.setStyleSheet("background: transparent;")
        
        conn_widget = QWidget()
        conn_box = QVBoxLayout(conn_widget)
        conn_box.setContentsMargins(0, 0, 0, 0)
        conn_box.setSpacing(8)

        for name, status in connectors:
            row = QHBoxLayout()
            c_lbl = QLabel(f"• {name}", conn_widget)
            c_lbl.setStyleSheet("font-size: 11px; color: rgba(255, 255, 255, 0.7);")
            
            st_lbl = QLabel(status, conn_widget)
            st_color = "#00E5CC" if status == "OK" else "rgba(255, 255, 255, 0.3)"
            st_lbl.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {st_color};")
            
            row.addWidget(c_lbl)
            row.addStretch()
            row.addWidget(st_lbl)
            conn_box.addLayout(row)

        conn_scroll.setWidget(conn_widget)
        layout.addWidget(conn_scroll, 1)

    def _on_mode_click(self, mode_key: str):
        self.mode_selected.emit(mode_key)

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = QWidget()
    win.setStyleSheet("background-color: #050510;")
    l = QHBoxLayout(win)
    p = ConnectorsPanel()
    l.addWidget(p)
    l.addStretch()
    win.resize(300, 600)
    win.show()
    sys.exit(app.exec())
