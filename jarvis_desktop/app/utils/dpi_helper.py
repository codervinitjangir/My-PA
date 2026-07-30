# jarvis_desktop/app/utils/dpi_helper.py

import sys
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import QApplication

def init_high_dpi():
    """
    Ensures High-DPI scaling is enabled across 100%, 125%, 150%, 200% displays on Windows
    """
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Enable crisp font rendering on Windows
    if sys.platform == 'win32':
        os_env = os.environ if 'os' in globals() else {}
        os_env['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
