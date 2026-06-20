# jarvis_desktop/styles.py

MAIN_STYLE = """
QWidget {
    background-color: #121212;
    color: #E0E0E0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 12px;
}

#presenceWindow {
    background-color: #1A1A1A;
    border: 1px solid #333333;
    border-radius: 10px;
}

QLabel {
    background: transparent;
}

#headerTitle {
    font-size: 14px;
    font-weight: bold;
    color: #4CAF50;
}

#infoLabel {
    color: #AAAAAA;
    padding: 2px 0;
}

QPushButton {
    background-color: #2A2A2A;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 5px 10px;
    color: #FFFFFF;
}

QPushButton:hover {
    background-color: #3A3A3A;
    border: 1px solid #555555;
}

QPushButton:pressed {
    background-color: #1A1A1A;
}

#talkButton {
    background-color: #1E3A8A;
    border: 1px solid #2563EB;
}
#talkButton:hover {
    background-color: #2563EB;
}
"""

TALK_DIALOG_STYLE = """
QDialog {
    background-color: #1A1A1A;
    border: 1px solid #2563EB;
    border-radius: 8px;
}
QLabel {
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
}
QPushButton {
    background-color: #B91C1C;
    border: 1px solid #DC2626;
    border-radius: 4px;
    padding: 5px;
    color: white;
}
QPushButton:hover {
    background-color: #DC2626;
}
"""
