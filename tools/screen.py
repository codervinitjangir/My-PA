"""Letting Bruno look at the screen, when asked.

This is the first thing Bruno can do that touches the world outside a
conversation, so the rule it establishes matters more than the code:

    Nothing is captured unless the user asked a question that needs it.

There is no timer, no background capture, and no buffer of past screens. A
screenshot is taken inside a tool call, sent, and dropped. Every capture is
logged, so there is a record of exactly when Bruno looked.

Encoding was chosen by measurement on a 1920x1080 display:

=========================  ========  =========
Setting                    Base64    Encode
=========================  ========  =========
Native PNG, level 6         267 KB      89 ms
Resized to 1400, PNG        571 KB     264 ms
Resized to 1400, JPEG 92    255 KB      79 ms
=========================  ========  =========

Native PNG wins on both size and fidelity, which is initially surprising:
resizing *increases* PNG size, because interpolation turns the flat colour
regions of a user interface into gradients that no longer compress. Lossless
also matters more here than for photographs -- the questions people ask about
a screen are usually about small text, which is what JPEG damages first.
"""

from __future__ import annotations

import base64
import io
import logging
import time
from typing import Any, Final

from core.display import enable_dpi_awareness
from core.protocols import ToolResult
from tools.registry import Tool

logger = logging.getLogger(__name__)

# Only shrinks images larger than this. A single monitor is untouched; a wall
# of 4K displays is brought down to something that uploads in a reasonable
# time on a slow connection.
MAX_DIMENSION: Final = 1920

# Pillow's default. Level 9 saves 0.2% for three times the time.
PNG_COMPRESS_LEVEL: Final = 6

# Above this, PNG has stopped being the right format. A desktop of windows and
# text compresses to about 170 KB; the same screen playing a video came out at
# 692 KB, because photographic content has none of the flat colour PNG exploits.
# JPEG handles exactly that content well, and its weakness -- smearing small
# text -- does not apply to a frame that is mostly video.
PNG_SIZE_LIMIT_BYTES: Final = 400_000
JPEG_QUALITY: Final = 88

NAME: Final = "look_at_screen"

# This description is the entire basis on which the model decides to call this,
# so it is prompt engineering rather than documentation. It names the indirect
# phrasings people actually use, because "look at my screen" is the one case
# that needs no help.
DESCRIPTION: Final = (
    "See what is on the user's display now. Call this whenever the answer "
    "depends on what is in front of them, which is far more often than they "
    "say the word 'screen': what is this, what does this say, what is this "
    "error, what am I looking at, where am I, what is playing, who is that, "
    "read this, is this right, and anything using 'this' or 'here' to point "
    "at something. If the question would only make sense to someone in the "
    "room with them, call this first. Not for general knowledge questions."
)


class ScreenCaptureError(RuntimeError):
    """The screen could not be captured."""


def capture(max_dimension: int = MAX_DIMENSION) -> tuple[str, int, int]:
    """Take a screenshot and encode it for the chat API.

    Args:
        max_dimension: Longest side to allow before downscaling.

    Returns:
        A ``(data_uri, width, height)`` triple.

    Raises:
        ScreenCaptureError: If no screen could be read.
    """
    # Without this a scaled display is captured at its virtual resolution,
    # which is the one case where fine text is lost before the model sees it.
    enable_dpi_awareness()

    try:
        from PIL import Image, ImageGrab
    except ImportError as exc:  # pragma: no cover -- Pillow is a hard dependency
        raise ScreenCaptureError(f"Image support is unavailable: {exc}") from exc

    started = time.perf_counter()
    try:
        # all_screens spans every monitor, so a question about "the other
        # window" works on a multi-monitor desk.
        shot = ImageGrab.grab(all_screens=True)
    except Exception as exc:  # noqa: BLE001 -- OS-specific failures are not enumerable
        raise ScreenCaptureError(f"Could not read the screen: {exc}") from exc

    if shot is None:
        raise ScreenCaptureError("The screen capture came back empty.")

    original = shot.size
    if max(shot.size) > max_dimension:
        shot.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    # RGBA would carry an alpha channel no display actually has, and some
    # endpoints reject it.
    flat = shot.convert("RGB")

    buffer = io.BytesIO()
    flat.save(buffer, format="PNG", compress_level=PNG_COMPRESS_LEVEL)
    raw = buffer.getvalue()
    media_type = "png"

    if len(raw) > PNG_SIZE_LIMIT_BYTES:
        buffer = io.BytesIO()
        flat.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        raw = buffer.getvalue()
        media_type = "jpeg"

    encoded = base64.b64encode(raw).decode("ascii")

    elapsed = (time.perf_counter() - started) * 1000
    logger.info(
        "Captured screen %dx%d%s as %s, %.0f KB, in %.0f ms",
        shot.size[0],
        shot.size[1],
        f" (from {original[0]}x{original[1]})" if shot.size != original else "",
        media_type.upper(),
        len(raw) / 1024,
        elapsed,
    )

    return f"data:image/{media_type};base64,{encoded}", shot.size[0], shot.size[1]


def _run(_arguments: dict[str, Any]) -> ToolResult:
    """Capture the screen. Takes no arguments deliberately.

    A tool with no parameters is the most reliable kind: there is nothing for
    the model to get wrong, and no argument parsing between the request and
    the result.
    """
    try:
        data_uri, width, height = capture()
    except ScreenCaptureError as exc:
        return ToolResult(f"I could not see the screen: {exc}")

    return ToolResult(
        content=f"Screenshot taken, {width} by {height} pixels. It follows.",
        images=(data_uri,),
    )


def screen_tool() -> Tool:
    """The screen-capture capability, ready to register."""
    return Tool(name=NAME, description=DESCRIPTION, run=_run)
