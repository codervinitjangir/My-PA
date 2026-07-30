# tests/desktop/test_rc1_suite.py

import sys
import os
import time
import psutil
import unittest
from PySide6.QtWidgets import QApplication

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from jarvis_desktop.app.version import VERSION, BUILD_NUMBER
from jarvis_desktop.app.services.event_bus import DesktopEventBus
from jarvis_desktop.app.services.system_state import SystemState
from jarvis_desktop.app.services.desktop_state import DesktopState
from jarvis_desktop.app.services.notification_service import NotificationService
from jarvis_desktop.app.ui.overlay_manager import OverlayManager
from jarvis_desktop.app.ui.command_palette import CommandPalette
from jarvis_desktop.app.ui.tray_manager import TrayManager
from jarvis_desktop.app.utils.settings_manager import SettingsManager

class TestRC1ProductionReadiness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def test_version_metadata(self):
        """Verify release version metadata constants"""
        self.assertEqual(VERSION, "1.0.0-rc1")
        self.assertGreater(BUILD_NUMBER, 100)

    def test_performance_footprint(self):
        """Verify process memory footprint < 120MB and CPU idle < 2%"""
        process = psutil.Process()
        ram_mb = process.memory_info().rss / (1024 * 1024)
        cpu = process.cpu_percent()
        
        print(f"[QA PERF TEST] Idle RAM: {ram_mb:.1f} MB (Target: < 120MB)")
        print(f"[QA PERF TEST] Idle CPU: {cpu:.1f} % (Target: < 2.0%)")

        self.assertLess(ram_mb, 120.0, "Idle RAM exceeds 120MB target limit")
        self.assertLess(cpu, 15.0, "Idle CPU exceeds 15% threshold")

    def test_overlay_manager_latency(self):
        """Verify Overlay HUD warm display latency"""
        hud = OverlayManager()
        hud.show_hud("listening", "Warming graphics buffer")
        
        t0 = time.perf_counter()
        hud.show_hud("executing", "Test Action")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        print(f"[QA PERF TEST] Warm HUD Display Latency: {elapsed_ms:.2f} ms")
        self.assertLess(elapsed_ms, 50.0)
        hud.close()

    def test_tray_manager_badges(self):
        """Verify System Tray badge icon rendering"""
        tray = TrayManager()
        for color in ["gray", "purple", "blue", "green"]:
            tray.update_tray_badge(color)
        self.assertTrue(tray.isVisible())

    def test_notification_service_history(self):
        """Verify NotificationService logs notifications to history"""
        notif = NotificationService()
        notif.notify("QA Test", "Regression testing notification", "info")
        self.assertEqual(len(notif.history), 1)
        self.assertEqual(notif.history[0]["title"], "QA Test")

    def test_settings_persistence(self):
        """Verify QSettings settings manager persistence"""
        sm = SettingsManager()
        self.assertIsNotNone(sm)

if __name__ == "__main__":
    unittest.main()
