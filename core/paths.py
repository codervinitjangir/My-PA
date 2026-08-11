"""Where Bruno's files live, in a source checkout and in a packaged build.

A checkout has one directory holding everything: code, the Piper binary, models,
and the voice. A packaged build has three, and confusing them is the classic way
to ship an executable that works on the machine that built it and nowhere else.

===============  ==========================  =============================
                 Running from source         Running as Bruno.exe
===============  ==========================  =============================
Code and         the repository              a temporary folder PyInstaller
bundled assets                               unpacks and later deletes
Downloaded       ``models/``, ``voices/``    ``%LOCALAPPDATA%\\Bruno``
Settings, key,   ``%LOCALAPPDATA%\\Bruno``      ``%LOCALAPPDATA%\\Bruno``
name, logs
===============  ==========================  =============================

Two rules follow, and every function here exists to enforce one of them. The
bundle directory is read-only and does not survive the process, so nothing may
be written to it. An installed program cannot write next to its own executable
either, since Program Files is not user-writable -- so downloads go to the same
per-user directory as the profile.

Keeping downloads in the repository when running from source is deliberate: it
means a developer's 200 MB of models are not re-fetched the first time they try
the packaged build, and vice versa.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)

APP_DIR_NAME: Final = "Bruno"

# What the directory was called before the project was renamed. Kept so an
# existing install does not silently lose the user's name and encrypted keys
# and ask them to set up again -- which, for the key in particular, means
# going back to a provider console to make a new one.
LEGACY_APP_DIR_NAME: Final = "EV"

# parents[2] is the repository root: bruno/core/paths.py -> bruno/core -> ev -> root.
# Only meaningful when running from source; see bundle_dir.
_SOURCE_ROOT: Final = Path(__file__).resolve().parents[2]


def is_frozen() -> bool:
    """Whether Bruno is running from a packaged executable."""
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> Path:
    """Directory holding read-only files shipped with Bruno.

    Under PyInstaller's one-file mode this is a temporary folder created at
    launch and deleted at exit, so nothing written here survives, and any path
    captured at import time in a previous run is already invalid.
    """
    unpacked = getattr(sys, "_MEIPASS", None)
    return Path(unpacked) if unpacked else _SOURCE_ROOT


def data_dir() -> Path:
    """Per-user directory for everything Bruno writes.

    Survives upgrades and reinstalls, which is why the profile and the API key
    live here rather than beside the executable.

    Returns:
        ``%LOCALAPPDATA%\\Bruno`` on Windows, ``~/.local/share/Bruno`` elsewhere.
    """
    if sys.platform == "win32":
        root = os.environ.get("LOCALAPPDATA")
        base = Path(root) if root else Path.home() / "AppData" / "Local"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_DIR_NAME


def adopt_legacy_data() -> bool:
    """Move settings from the pre-rename directory, once.

    Returns:
        True if anything was carried over.
    """
    current = data_dir()
    if current.exists():
        return False

    legacy = current.parent / LEGACY_APP_DIR_NAME
    if not legacy.is_dir():
        return False

    try:
        legacy.rename(current)
    except OSError:
        logger.warning("Could not carry settings over from %s", legacy, exc_info=True)
        return False

    logger.info("Carried settings over from %s", legacy)
    return True


def downloads_dir() -> Path:
    """Root for assets fetched at first run.

    The repository when running from source, so a checkout keeps using the
    models it already has; the per-user data directory when packaged, because
    the bundle is read-only and temporary.
    """
    return data_dir() if is_frozen() else _SOURCE_ROOT


def models_dir() -> Path:
    """Speech recognition weights."""
    return downloads_dir() / "models"


def voices_dir() -> Path:
    """Piper voice models."""
    return downloads_dir() / "voices"


def piper_binary() -> Path:
    """The Piper executable, which ships inside the bundle rather than downloading.

    It is program code, not user data: it belongs in the install for the same
    reason the Python runtime does, and there is no benefit to fetching 59 MB
    of unchanging binary on every machine's first run.
    """
    return bundle_dir() / "vendor" / "piper" / "piper.exe"


def env_file() -> Path:
    """Optional dotenv overrides.

    Only present in a checkout. A packaged install is configured through the
    setup dialog and the tray menu, not by editing a file the user would have
    to find first.
    """
    return _SOURCE_ROOT / ".env"


def describe() -> str:
    """A human-readable dump of every resolved location, for diagnostics."""
    mode = "packaged" if is_frozen() else "source"
    rows = (
        ("mode", mode),
        ("bundle", bundle_dir()),
        ("data", data_dir()),
        ("models", models_dir()),
        ("voices", voices_dir()),
        ("piper", piper_binary()),
    )
    width = max(len(label) for label, _ in rows)
    return "\n".join(f"  {label:<{width}}  {value}" for label, value in rows)
