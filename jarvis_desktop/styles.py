# jarvis_desktop/styles.py

MAIN_STYLE = """
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    color: #E0E0E0;
}

#presenceWindow {
    background-color: rgba(15, 15, 15, 245);
    border: 1px solid rgba(255, 255, 255, 25);
    border-radius: 16px;
}

#miniExpandWindow {
    background-color: rgba(15, 15, 15, 245);
    border: 1px solid rgba(255, 255, 255, 25);
    border-radius: 20px;
}

#miniLabel {
    color: #4CAF50;
    font-size: 16px;
    font-weight: bold;
}

QLabel {
    background: transparent;
    font-size: 11px;
}

#headerTitle {
    font-size: 13px;
    font-weight: bold;
    color: #FFFFFF;
}

#infoLabel {
    color: #E8E8E8;
    padding: 6px;
    font-size: 12px;
    line-height: 1.4;
}

QPushButton {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(50, 50, 50, 200), stop:1 rgba(30, 30, 30, 200));
    border: 1px solid rgba(255, 255, 255, 20);
    border-radius: 8px;
    padding: 8px 12px;
    color: #FFFFFF;
    font-size: 11px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(70, 70, 70, 220), stop:1 rgba(45, 45, 45, 220));
    border: 1px solid rgba(255, 255, 255, 40);
}

QPushButton:pressed {
    background-color: rgba(25, 25, 25, 250);
}

QLineEdit {
    background-color: rgba(0, 0, 0, 120);
    border: 1px solid rgba(255, 255, 255, 30);
    border-radius: 8px;
    padding: 8px 12px;
    color: #FFFFFF;
    font-size: 12px;
}

QLineEdit:focus {
    border: 1px solid #4CAF50;
    background-color: rgba(10, 10, 10, 200);
}

#wakeWordBtn {
    color: #FFC107;
}

#minimizeBtn, #hideBtn {
    background: transparent;
    border: none;
    font-size: 10px;
    color: #888888;
}

#minimizeBtn:hover, #hideBtn:hover {
    color: #FFFFFF;
}

QScrollArea {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    border: none;
    background: rgba(30, 30, 30, 100);
    width: 6px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: rgba(100, 100, 100, 150);
    min-height: 20px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(150, 150, 150, 200);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""
