"""Logging setup shared by every entry point.

Two audiences with opposite needs. A developer running a demo script wants
Bruno's INFO messages on screen. Someone who installed Bruno wants a clean startup
and no mention of ctranslate2 -- but when something breaks, the detail has to
have been recorded somewhere findable, because a tray application has no
console to have printed it to.

So the file always gets everything and the console gets whatever was asked
for. Third-party libraries are pinned to WARNING on the console regardless:
their per-request INFO lines print into the middle of streaming replies,
corrupting the output being read.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Final

# Libraries that log routine, per-request activity at INFO.
_NOISY_LOGGERS: Final = (
    "httpx",
    "httpcore",
    "openai",
    "urllib3",
    "huggingface_hub",
    "faster_whisper",
)

_CONSOLE_FORMAT: Final = "%(levelname)-8s %(name)s: %(message)s"
_FILE_FORMAT: Final = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"

LOG_FILE_NAME: Final = "bruno.log"
MAX_LOG_BYTES: Final = 1_000_000
LOG_BACKUPS: Final = 2


def log_path() -> Path:
    """Where Jarvis writes its log."""
    from core import paths

    return paths.data_dir() / "logs" / LOG_FILE_NAME


def configure(
    level: str = "INFO",
    *,
    quiet_libraries: bool = True,
    to_file: bool = False,
    console: bool = True,
) -> None:
    """Set up logging.

    Args:
        level: Level for Bruno's own loggers on the console.
        quiet_libraries: Hold third-party loggers at WARNING on the console.
            Disable when diagnosing a network or model-loading problem, where
            those messages are the ones you want.
        to_file: Also write a rotating DEBUG log to :func:`log_path`. Enabled
            by the tray application, where nothing is visible otherwise.
        console: Emit to stderr at all. False for a windowed build, which has
            no console attached.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    if console:
        stream = logging.StreamHandler()
        stream.setLevel(level)
        stream.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
        if quiet_libraries:
            stream.addFilter(_LibraryFilter())
        root.addHandler(stream)

    if to_file:
        _add_file_handler(root)


def _add_file_handler(root: logging.Logger) -> None:
    """Attach a rotating file handler, ignoring failure.

    An unwritable disk should not stop Bruno from running; it only means a
    problem later will be harder to diagnose.
    """
    path = log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            path, maxBytes=MAX_LOG_BYTES, backupCount=LOG_BACKUPS, encoding="utf-8"
        )
    except OSError:
        logging.getLogger(__name__).warning("Could not open the log file at %s", path)
        return

    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(_FILE_FORMAT))
    root.addHandler(handler)


class _LibraryFilter(logging.Filter):
    """Drops routine third-party chatter from the console only."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= logging.WARNING:
            return True
        return not any(
            record.name == name or record.name.startswith(name + ".")
            for name in _NOISY_LOGGERS
        )
