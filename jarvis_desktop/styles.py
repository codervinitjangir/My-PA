# jarvis_desktop/styles.py

MAIN_STYLE = """
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    color: #E0E0E0;
}

#presenceWindow {
    background-color: rgba(20, 20, 20, 230);
    border: 1px solid rgba(80, 80, 80, 150);
    border-radius: 12px;
}

#miniExpandWindow {
    background-color: rgba(20, 20, 20, 230);
    border: 1px solid rgba(80, 80, 80, 150);
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
    font-size: 12px;
    font-weight: bold;
    color: #FFFFFF;
}

#infoLabel {
    color: #AAAAAA;
    padding: 2px 0;
    font-size: 11px;
}

QPushButton {
    background-color: rgba(40, 40, 40, 200);
    border: 1px solid rgba(80, 80, 80, 150);
    border-radius: 6px;
    padding: 6px 10px;
    color: #FFFFFF;
    font-size: 11px;
}

QPushButton:hover {
    background-color: rgba(60, 60, 60, 220);
    border: 1px solid rgba(100, 100, 100, 180);
}

QPushButton:pressed {
    background-color: rgba(30, 30, 30, 250);
}

#wakeWordBtn {
    color: #FFC107;
}

#hideBtn {
    background: transparent;
    border: none;
    font-size: 10px;
    color: #888888;
}
#hideBtn:hover {
    color: #FFFFFF;
}
"""
