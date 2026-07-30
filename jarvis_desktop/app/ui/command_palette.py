# jarvis_desktop/app/ui/command_palette.py

import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel, QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QGuiApplication

class CommandPalette(QDialog):
    """
    Raycast / Spotlight / PowerToys Run style Command Palette.
    Supports instant autocomplete, category filtering (Actions, Files, Memory, Commands, Recent, Settings),
    and keyboard navigation (Up, Down, Enter, ESC).
    """
    command_executed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(620, 380)

        # Main Container Frame
        card = QFrame(self)
        card.setObjectName("paletteCard")
        card.setStyleSheet("""
            QFrame#paletteCard {
                background-color: #0a0a1e;
                border: 1px solid rgba(124, 106, 239, 0.4);
                border-radius: 16px;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)

        # Search Bar
        search_layout = QHBoxLayout()
        search_icon = QLabel("🔍", card)
        search_icon.setStyleSheet("font-size: 16px;")

        self.input_field = QLineEdit(card)
        self.input_field.setPlaceholderText("Search commands, actions, memory...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 15px;
                font-weight: 500;
                selection-background-color: #7c6aef;
            }
        """)
        self.input_field.textChanged.connect(self._filter_commands)

        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.input_field, 1)
        card_layout.addLayout(search_layout)

        # Divider
        divider = QFrame(card)
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.08);")
        card_layout.addWidget(divider)

        # Results List Widget
        self.list_widget = QListWidget(card)
        self.list_widget.setFrameShape(QFrame.NoFrame)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                color: #ffffff;
                font-size: 13px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px 14px;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background-color: rgba(124, 106, 239, 0.25);
                border: 1px solid #7c6aef;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.06);
            }
        """)
        self.list_widget.itemActivated.connect(self._on_item_activated)
        card_layout.addWidget(self.list_widget)

        # Footer Hint
        footer = QLabel("↑ ↓ to navigate • ↵ to select • esc to close", card)
        footer.setStyleSheet("font-size: 10px; color: rgba(255, 255, 255, 0.4); text-align: center;")
        footer.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(footer)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(card)

        # Default Available Commands
        self.all_commands = [
            ("⚡ Open VS Code", "Actions", "Open VS Code"),
            ("🌅 Morning Brief", "Actions", "Morning Brief"),
            ("👁 Analyze Screen", "Actions", "Analyze Screen"),
            ("▶ Resume Session", "Recent", "Continue Previous Session"),
            ("🌐 Quick Links", "Commands", "Quick Links"),
            ("📝 Add Friction", "Commands", "Add Friction"),
            ("🔄 Refresh Dashboard", "Actions", "Refresh Dashboard"),
            ("⚙️ Open Settings", "Settings", "Open Settings"),
            ("🧠 Search Memory", "Memory", "Search Memory")
        ]

        self.input_field.installEventFilter(self)
        self._populate_list(self.all_commands)
        self._center_on_screen()

    def _center_on_screen(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = screen.top() + (screen.height() // 4)
        self.move(x, y)

    def _populate_list(self, commands):
        self.list_widget.clear()
        for title, category, cmd in commands:
            item = QListWidgetItem(f"{title}   [{category}]")
            item.setData(Qt.UserRole, cmd)
            self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _filter_commands(self, text: str):
        query = text.strip().lower()
        if not query:
            self._populate_list(self.all_commands)
            return
        filtered = [
            (t, cat, cmd) for t, cat, cmd in self.all_commands
            if query in t.lower() or query in cat.lower() or query in cmd.lower()
        ]
        self._populate_list(filtered)

    def eventFilter(self, obj, event):
        if obj == self.input_field and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Down:
                cur = self.list_widget.currentRow()
                if cur < self.list_widget.count() - 1:
                    self.list_widget.setCurrentRow(cur + 1)
                return True
            elif key == Qt.Key_Up:
                cur = self.list_widget.currentRow()
                if cur > 0:
                    self.list_widget.setCurrentRow(cur - 1)
                return True
            elif key == Qt.Key_Return:
                item = self.list_widget.currentItem()
                if item:
                    self._on_item_activated(item)
                return True
            elif key == Qt.Key_Escape:
                self.reject()
                return True
        return super().eventFilter(obj, event)

    def _on_item_activated(self, item):
        cmd = item.data(Qt.UserRole)
        if cmd:
            self.command_executed.emit(cmd)
        self.accept()

    def show_palette(self):
        self.input_field.clear()
        self._populate_list(self.all_commands)
        self._center_on_screen()
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_field.setFocus()

# ── Standalone Preview Test ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    palette = CommandPalette()
    palette.command_executed.connect(lambda cmd: print(f"Executed: {cmd}"))
    palette.show_palette()
    sys.exit(app.exec())
