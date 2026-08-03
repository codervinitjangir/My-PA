# jarvis_desktop/app.py

import sys
import os
import asyncio
import qasync
import threading
from PySide6.QtWidgets import QApplication

from jarvis_desktop.app.utils.dpi_helper import init_high_dpi
from jarvis_desktop.app.ui.main_window import MainWindow
from jarvis_desktop.app.services.backend_service import BackendService
from jarvis_desktop.app.controllers.main_controller import MainController

# Import the background engines
import jarvis_desktop.laptop_client as laptop_client

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
    # Use the SERVER_URL already detected by laptop_client (handles local/Render fallback)
    backend_url = laptop_client.SERVER_URL
    backend_service = BackendService(base_url=backend_url)
    main_window = MainWindow()

    # 3. Instantiate Controller
    controller = MainController(main_window, backend_service)

    # 4. Show Window
    main_window.show()

    # 5. Start Background Engines
    asyncio.create_task(backend_service.check_health())
    asyncio.create_task(backend_service.fetch_dashboard())
    
    # Start the laptop client websocket loop in the background
    asyncio.create_task(laptop_client.connect_and_listen())

    # Keep async event loop alive
    while main_window.isVisible():
        await asyncio.sleep(0.1)

    await backend_service.close()
    laptop_client.QUIT_FLAG = True

def main():
    # 1. Enable High-DPI scaling before QApplication creation
    init_high_dpi()

    # 2. Start Wake Word thread if enabled
    if laptop_client.WAKE_WORD_ENABLED:
        threading.Thread(target=laptop_client.wake_word_thread, daemon=True).start()

    # 3. Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS Desktop")

    # 4. Create qasync Event Loop
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        loop.run_until_complete(main_async(app))

if __name__ == "__main__":
    main()
