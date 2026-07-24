"""
app/core/security/allowlist.py — Security Allow-List Enforcement Engine

Enforces strict security allow-lists for launched desktop applications, shell targets, and URLs.
Prevents arbitrary command execution and path traversal attacks.
"""

import os
import re
import urllib.parse
import logging
from typing import Tuple, Optional

logger = logging.getLogger("J.A.R.V.I.S.Security")

# Allowed application aliases & executable names
ALLOWED_APP_TARGETS = {
    "notepad", "notepad.exe",
    "calculator", "calc", "calc.exe",
    "cmd", "cmd.exe",
    "powershell", "powershell.exe",
    "explorer", "explorer.exe",
    "chrome", "chrome.exe",
    "code", "vscode", "code.exe",
    "telegram", "telegram.exe",
    "spotify", "spotify.exe",
    "vlc", "vlc.exe",
    "mspaint", "mspaint.exe",
    "system:lock_screen", "lock_screen", "lock_pc", "lock"
}

# Allowed URL schemes
ALLOWED_URL_SCHEMES = {"http", "https"}

def is_safe_app_target(target: str) -> Tuple[bool, str]:
    """
    Validate if a target desktop application name or file path is allowed for launch.
    Returns (is_safe: bool, sanitized_target_or_reason: str).
    """
    if not target or not isinstance(target, str):
        return False, "Target must be a non-empty string"

    target_clean = target.strip().lower()

    # Block path traversal attempts
    if ".." in target_clean or "/" in target_clean and not target_clean.startswith("http"):
        return False, "Path traversal sequence not allowed"

    # Check against explicit application allow-list
    basename = os.path.basename(target_clean)
    if basename in ALLOWED_APP_TARGETS or target_clean in ALLOWED_APP_TARGETS:
        return True, target.strip()

    # Check system standard Windows AppData / Program Files paths
    if any(target_clean.endswith(ext) for ext in [".exe", ".lnk", ".appref-ms"]):
        program_files = os.getenv("ProgramFiles", "C:\\Program Files").lower()
        program_files_x86 = os.getenv("ProgramFiles(x86)", "C:\\Program Files (x86)").lower()
        appdata = os.getenv("APPDATA", "").lower()
        localappdata = os.getenv("LOCALAPPDATA", "").lower()

        if any(target_clean.startswith(p) for p in [program_files, program_files_x86, appdata, localappdata] if p):
            return True, target.strip()

    logger.warning("[SECURITY] Blocked unauthorized desktop launch target: '%s'", target)
    return False, f"Target '{target}' is not in the security allow-list"


def is_safe_url(url: str) -> Tuple[bool, str]:
    """
    Validate if a URL string is safe for opening in browser.
    Returns (is_safe: bool, sanitized_url_or_reason: str).
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"

    url_clean = url.strip()
    parsed = urllib.parse.urlparse(url_clean)

    if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
        return False, f"URL scheme '{parsed.scheme}' is not allowed (only http/https)"

    if not parsed.netloc:
        return False, "Invalid URL host"

    return True, url_clean
