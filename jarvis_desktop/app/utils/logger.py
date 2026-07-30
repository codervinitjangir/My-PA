# jarvis_desktop/app/utils/logger.py

import os
import sys
import datetime

class DesktopLogger:
    """
    Structured Logging System writing to logs/jarvis_desktop.log
    with category filters, clear logs, and open log directory helpers.
    """
    def __init__(self):
        self.log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "jarvis_desktop.log")

    def _write_log(self, level: str, category: str, message: str):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] [{level}] [{category}] {message}\n"
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            pass

    def info(self, category: str, message: str):
        self._write_log("INFO", category, message)

    def warning(self, category: str, message: str):
        self._write_log("WARN", category, message)

    def error(self, category: str, message: str):
        self._write_log("ERROR", category, message)

    def perf(self, category: str, metric_name: str, value_ms: float):
        self._write_log("PERF", category, f"{metric_name}: {value_ms:.2f}ms")

    def clear_logs(self):
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, "w", encoding="utf-8") as f:
                    f.write("")
        except Exception as e:
            print(f"Failed to clear logs: {e}")

    def get_log_path(self) -> str:
        return self.log_file

logger = DesktopLogger()
