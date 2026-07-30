# jarvis_desktop/app/utils/crash_manager.py

import sys
import os
import traceback
import datetime
from PySide6.QtWidgets import QMessageBox

class CrashManager:
    """
    Unhandled Exception Interceptor & Crash Manager.
    Captures unhandled runtime errors, logs detailed crash dumps to logs/crash_<timestamp>.log,
    and displays a user recovery prompt.
    """
    def __init__(self):
        self.log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
        os.makedirs(self.log_dir, exist_ok=True)
        self.original_excepthook = sys.excepthook
        sys.excepthook = self._handle_uncaught_exception

    def _handle_uncaught_exception(self, exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H%M%S")
        crash_file = os.path.join(self.log_dir, f"crash_{timestamp}.log")

        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

        try:
            with open(crash_file, "w", encoding="utf-8") as f:
                f.write(f"=== JARVIS DESKTOP CRASH DUMP ===\nTimestamp: {timestamp}\n\n{err_msg}\n")
        except Exception:
            pass

        print(f"[CrashManager] Unhandled crash saved to {crash_file}:\n{err_msg}")

        # Show user-friendly error recovery dialog
        try:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("JARVIS Error Recovery")
            msg.setText("JARVIS encountered an unexpected issue.")
            msg.setInformativeText(f"A crash dump has been saved to:\n{crash_file}\n\nThe application will attempt to continue running.")
            msg.exec()
        except Exception:
            pass

crash_manager = CrashManager()
