"""
scroll_controller.py — Voice-controlled scroll via Windows native API.

Uses ctypes SendInput (MOUSEEVENTF_WHEEL) — no pyautogui, no subprocess,
no extra dependencies. Pure Windows API, ships with every Python install.

Security profile:
  ✅ Read-only viewport movement — cannot click, type, or exfiltrate data
  ✅ No file system access
  ✅ No network access
  ✅ No keyboard injection
  ✅ Fails silently on non-Windows
"""
import ctypes
import logging
import re
import time

logger = logging.getLogger("J.A.R.V.I.S")

# Windows MOUSEEVENTF_WHEEL flag
_MOUSEEVENTF_WHEEL = 0x0800
# One standard scroll notch (Windows convention = 120 units)
_WHEEL_DELTA = 120


def _scroll(clicks: int) -> bool:
    """
    Send a scroll event to whatever window currently has focus.
    Positive clicks = scroll UP, negative = scroll DOWN.
    """
    try:
        delta = ctypes.c_long(_WHEEL_DELTA * clicks)
        ctypes.windll.user32.mouse_event(_MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
        return True
    except Exception as e:
        logger.error(f"[Scroll] Failed: {e}")
        return False


def _scroll_repeated(clicks_per_tick: int, ticks: int, delay: float = 0.05) -> bool:
    """Smooth large scrolls broken into multiple ticks."""
    ok = True
    for _ in range(ticks):
        ok = ok and _scroll(clicks_per_tick)
        if ticks > 1:
            time.sleep(delay)
    return ok


# ── Intent Detection ────────────────────────────────────────────────────────────

_MAGNITUDE_WORDS = re.compile(
    r"\b(a lot|lots|much|far|fast|quickly|more|big|large|all the way|completely)\b",
    re.IGNORECASE
)

_SCROLL_PATTERNS = [
    # "scroll down / up"
    (re.compile(r"\bscroll\s+down\b", re.IGNORECASE), "down"),
    (re.compile(r"\bscroll\s+up\b",   re.IGNORECASE), "up"),
    # "go down / go up"
    (re.compile(r"\bgo\s+down\b",     re.IGNORECASE), "down"),
    (re.compile(r"\bgo\s+up\b",       re.IGNORECASE), "up"),
    # "move down / move up"
    (re.compile(r"\bmove\s+down\b",   re.IGNORECASE), "down"),
    (re.compile(r"\bmove\s+up\b",     re.IGNORECASE), "up"),
    # "page down / page up"
    (re.compile(r"\bpage\s+down\b",   re.IGNORECASE), "down_big"),
    (re.compile(r"\bpage\s+up\b",     re.IGNORECASE), "up_big"),
    # "go to / scroll to top / bottom"
    (re.compile(r"\b(go|scroll)\s+to\s+(the\s+)?top\b",    re.IGNORECASE), "top"),
    (re.compile(r"\b(go|scroll)\s+to\s+(the\s+)?bottom\b", re.IGNORECASE), "bottom"),
    (re.compile(r"\b(go|scroll)\s+to\s+(the\s+)?end\b",    re.IGNORECASE), "bottom"),
    (re.compile(r"\b(go|scroll)\s+to\s+(the\s+)?start\b",  re.IGNORECASE), "top"),
]


def parse_scroll_intent(text: str):
    """
    Returns (direction, big) if text contains a scroll command, else None.
    direction: 'up' | 'down' | 'top' | 'bottom'
    big: True if the user asked for a large scroll
    """
    for pattern, direction in _SCROLL_PATTERNS:
        if pattern.search(text):
            big = bool(_MAGNITUDE_WORDS.search(text))
            return direction, big
    return None


def execute_scroll_command(text: str) -> str:
    """
    Parses and executes a scroll command from voice text.
    Returns a short spoken confirmation string.
    """
    intent = parse_scroll_intent(text)
    if not intent:
        return None  # not a scroll command

    direction, big = intent

    if direction == "top":
        _scroll_repeated(15, 8)
        return "Scrolled to the top."

    if direction == "bottom":
        _scroll_repeated(-15, 8)
        return "Scrolled to the bottom."

    if direction == "down_big" or (direction == "down" and big):
        _scroll_repeated(-5, 4)
        return "Scrolled down."

    if direction == "up_big" or (direction == "up" and big):
        _scroll_repeated(5, 4)
        return "Scrolled up."

    if direction == "down":
        _scroll(-3)
        return "Scrolled down."

    if direction == "up":
        _scroll(3)
        return "Scrolled up."

    return None
