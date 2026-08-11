"""Display-related Windows settings shared by the UI and screen capture.

Lives here rather than in either caller because both need it and neither owns
it: dialogs need it so they are not rendered blurry, and screen capture needs
it so a screenshot is taken at real pixels instead of a scaled approximation.
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_done = threading.Event()

# Per-monitor awareness would be better on mixed-DPI setups, but it also makes
# the application responsible for rescaling its own windows when they move
# between monitors, which Tk does not do. System awareness is the setting that
# is right far more often than it is wrong.
_SYSTEM_DPI_AWARE = 1


def enable_dpi_awareness() -> bool:
    """Tell Windows this process handles high-DPI displays itself.

    Without it Windows renders at 96 DPI and stretches the result: dialogs look
    blurry, and a screenshot of a scaled display comes back at the virtual
    resolution rather than the real one, losing exactly the fine text that a
    question about the screen is usually about.

    Must run before any window is created. Idempotent, and safe to call from
    anywhere, since the setting is per-process and cannot be changed once
    windows exist.

    Returns:
        True if awareness is in effect. Failure is not worth reporting to the
        user -- a slightly soft window beats no window.
    """
    if _done.is_set():
        return True

    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(_SYSTEM_DPI_AWARE)  # type: ignore[attr-defined]
    except OSError:
        # Already set, usually because something called this first. That is
        # the desired end state, so treat it as success.
        _done.set()
        return True
    except Exception:  # noqa: BLE001 -- cosmetic, and absent on non-Windows
        logger.debug("Could not enable DPI awareness", exc_info=True)
        return False

    _done.set()
    return True
