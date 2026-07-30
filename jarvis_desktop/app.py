# jarvis_desktop/app.py

import sys
import os
import asyncio
import qasync
from PySide6.QtWidgets import QApplication

from jarvis_desktop.app.utils.dpi_helper import init_high_dpi
from jarvis_desktop.app.ui.main_window import MainWindow
from jarvis_desktop.app.services.backend_service import BackendService
from jarvis_desktop.app.controllers.main_controller import MainController

def load_stylesheet(app: QApplication):
    """Load master jarvis.qss stylesheet"""
    qss_path = os.path.join(os.path.dirname(__file__), "app", "styles", "jarvis.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

async def main_async(app: QApplication):
    """Asynchronous main function running inside qasync event loop"""
    # 1. Load stylesheet
    load_stylesheet(app)

    # 2. Instantiate Services & Window
    backend_service = BackendService(base_url="http://127.0.0.1:8000")
    main_window = MainWindow()

    # 3. Instantiate Controller
    controller = MainController(main_window, backend_service)

    # 4. Show Window
    main_window.show()

    # 5. Initial Health & Dashboard Fetch
    asyncio.create_task(backend_service.check_health())
    asyncio.create_task(backend_service.fetch_dashboard())

    # Keep async event loop alive
    while main_window.isVisible():
        await asyncio.sleep(0.1)

    await backend_service.close()

def main():
    # 1. Enable High-DPI scaling before QApplication creation
    init_high_dpi()

    # 2. Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS Desktop")

    # 3. Create qasync Event Loop
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        loop.run_until_complete(main_async(app))

if __name__ == "__main__":
    main()
