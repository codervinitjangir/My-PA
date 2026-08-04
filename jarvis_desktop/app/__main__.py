# jarvis_desktop/app/__main__.py

import sys
import os
import asyncio
import qasync
from PySide6.QtWidgets import QApplication

from jarvis_desktop.app.utils.dpi_helper import init_high_dpi
from jarvis_desktop.app.services.backend_service import BackendService
from jarvis_desktop.app.services.desktop_service_layer import DesktopServiceLayer
from jarvis_desktop.app.services.notification_service import NotificationService
from jarvis_desktop.app.services.plugin_interface import PluginManager
from jarvis_desktop.app.ui.window_manager import WindowManager
from jarvis_desktop.app.controllers.main_controller import MainController

def load_stylesheet(app: QApplication):
    """Load master jarvis.qss stylesheet"""
    qss_path = os.path.join(os.path.dirname(__file__), "styles", "jarvis.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

async def main_async(app: QApplication):
    """Asynchronous main function running inside qasync event loop"""
    load_stylesheet(app)

    # 1. Core Services & Desktop Service Layer
    backend_service = BackendService(base_url="http://127.0.0.1:8000")
    desktop_service = DesktopServiceLayer(backend_service)

    # 2. Window Manager & UI Lifecycle
    win_mgr = WindowManager(backend_service)
    notif_service = NotificationService(win_mgr.tray)
    plugin_mgr = PluginManager(desktop_service.bus)

    # 3. Main Controller Integration
    controller = MainController(
        win_mgr.main_win,
        backend_service,
        desktop_service.system_state,
        desktop_service.desktop_state
    )

    # Show initial view
    win_mgr.show_main_window()

    # Initial Health & Dashboard Fetch (with retry)
    async def health_loop():
        """Retry health check every 30s — auto-reconnects when backend comes online."""
        while win_mgr.main_win.isVisible() or win_mgr.tray.isVisible():
            try:
                is_online = await backend_service.check_health()
                if is_online:
                    await backend_service.fetch_dashboard()
            except Exception:
                pass
            await asyncio.sleep(30)

    asyncio.create_task(health_loop())

    try:
        while win_mgr.main_win.isVisible() or win_mgr.tray.isVisible():
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass
    finally:
        await backend_service.close()

def main():
    init_high_dpi()

    # Launch local backend server automatically
    backend_process = None
    try:
        import subprocess
        backend_process = subprocess.Popen([sys.executable, "run.py"])
        print("[JARVIS] Auto-started local backend server.")
    except Exception as e:
        print(f"[JARVIS] Failed to auto-start backend: {e}")

    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS Desktop")
    app.setQuitOnLastWindowClosed(False)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    try:
        with loop:
            loop.run_until_complete(main_async(app))
    except (KeyboardInterrupt, SystemExit, RuntimeError):
        pass
    finally:
        if backend_process:
            print("[JARVIS] Shutting down local backend server...")
            backend_process.terminate()

if __name__ == "__main__":
    main()
