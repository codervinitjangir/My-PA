"""
deploy/register_autostart.py — Windows Auto-Start Registration (Opt-in)
========================================================================

Creates a Windows Registry Run key so laptop_client.py starts automatically
on user login.  This script is deliberately a ONE-TIME manual step, not
called by any installer or main process.

Usage (run once from project root, as the login user):
    python deploy/register_autostart.py          # register
    python deploy/register_autostart.py --remove  # remove

What it does:
    Writes to HKEY_CURRENT_USER\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run
    Value name : JARVIS_LaptopClient
    Value data : "C:\\path\\to\\python.exe" "C:\\path\\to\\laptop_client.py"

Why HKCU (not HKLM):
    HKCU requires NO admin rights, only affects the current user, and is
    the recommended location for per-user startup entries.  HKLM would
    require elevation and affect all users — not what we want.

Why registry instead of Startup folder shortcut:
    Registry Run keys survive renames of the Startup folder and work
    identically in all Windows 10/11 editions.  We also write a Startup
    folder entry as a human-visible backup (user can see it in Task Manager
    → Startup apps tab).

Safety notes:
    - Does NOT execute anything immediately.
    - Does NOT modify any JARVIS server (main.py / run.py) — only the laptop
      client relay.
    - Can be fully reversed with --remove.
    - Uses winreg (stdlib) — no third-party packages needed.
"""

import argparse
import os
import sys
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────

_ENTRY_NAME = "JARVIS_LaptopClient"
_REGISTRY_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"

# Resolve paths relative to this script's location so it works regardless of CWD
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_LAPTOP_CLIENT = _PROJECT_ROOT / "laptop_client.py"


def _get_python_executable() -> Path:
    """
    Returns the Python executable to use.

    Priority:
      1. .venv in project root (most common dev setup)
      2. sys.executable (whatever is running this script right now)
    """
    venv_python = _PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return venv_python
    return Path(sys.executable)


def _build_command_string(python: Path, client: Path) -> str:
    """
    Wraps both paths in quotes and combines them into the registry value string.
    Windows treats the value as a command line, so quoting is critical for paths
    containing spaces (e.g. "Persnoal Pro").
    """
    return f'"{python}" "{client}"'


# ── Registry helpers ──────────────────────────────────────────────────────────

def _check_platform():
    if sys.platform != "win32":
        print("ERROR: This script is Windows-only.")
        print(f"       Current platform: {sys.platform}")
        sys.exit(1)


def register(verbose: bool = True) -> None:
    """
    Registers JARVIS laptop client in Windows Registry Run key.
    Also adds a .bat launcher to the user's Startup folder as a visible backup.
    """
    _check_platform()

    import winreg  # stdlib, Windows-only

    python = _get_python_executable()
    cmd = _build_command_string(python, _LAPTOP_CLIENT)

    # Validate the paths before writing anything
    if not _LAPTOP_CLIENT.exists():
        print(f"ERROR: laptop_client.py not found at: {_LAPTOP_CLIENT}")
        print("       Please run this script from the project root.")
        sys.exit(1)

    if verbose:
        print("=" * 60)
        print("  J.A.R.V.I.S — Windows Auto-Start Registration")
        print("=" * 60)
        print(f"  Python     : {python}")
        print(f"  Client     : {_LAPTOP_CLIENT}")
        print(f"  Command    : {cmd}")
        print()

    # ── 1. Write Registry Run key ──────────────────────────────────────────────
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, _ENTRY_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        if verbose:
            print(f"[OK] Registry key written:")
            print(f"     HKCU\\{_REGISTRY_KEY}")
            print(f"     {_ENTRY_NAME} = {cmd}")
    except PermissionError:
        print("ERROR: Cannot write to registry. Try running as the correct user (no elevation needed for HKCU).")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Registry write failed: {e}")
        sys.exit(1)

    # ── 2. Write Startup folder .bat (human-visible, Task Manager shows it) ───
    try:
        startup_folder = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        bat_path = startup_folder / "JARVIS_LaptopClient.bat"

        bat_content = f"""@echo off
REM J.A.R.V.I.S Laptop Client — auto-start entry
REM Registered by: deploy/register_autostart.py
REM Remove with  : python deploy/register_autostart.py --remove
title J.A.R.V.I.S Laptop Client
{cmd}
"""
        bat_path.write_text(bat_content, encoding="utf-8")
        if verbose:
            print(f"\n[OK] Startup folder .bat written:")
            print(f"     {bat_path}")
            print("     (Visible in Task Manager → Startup apps tab)")
    except Exception as e:
        # Non-fatal: registry entry is the primary mechanism
        if verbose:
            print(f"[WARN] Could not write Startup folder .bat: {e}")
            print("       Registry entry still active — startup will still work.")

    if verbose:
        print()
        print("✅  Done. JARVIS laptop client will start automatically on next login.")
        print("    To remove, run: python deploy/register_autostart.py --remove")
        print("=" * 60)


def remove(verbose: bool = True) -> None:
    """
    Removes the JARVIS auto-start registry entry and Startup folder .bat.
    Safe to run even if entries don't exist.
    """
    _check_platform()

    import winreg

    if verbose:
        print("=" * 60)
        print("  J.A.R.V.I.S — Removing Auto-Start Entries")
        print("=" * 60)

    # ── Remove Registry entry ─────────────────────────────────────────────────
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, _ENTRY_NAME)
        winreg.CloseKey(key)
        if verbose:
            print(f"[OK] Registry entry removed: {_ENTRY_NAME}")
    except FileNotFoundError:
        if verbose:
            print("[INFO] Registry entry not found (already removed or never registered).")
    except Exception as e:
        print(f"[WARN] Could not remove registry entry: {e}")

    # ── Remove Startup .bat ───────────────────────────────────────────────────
    try:
        startup_folder = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        bat_path = startup_folder / "JARVIS_LaptopClient.bat"
        if bat_path.exists():
            bat_path.unlink()
            if verbose:
                print(f"[OK] Startup folder .bat removed: {bat_path}")
        else:
            if verbose:
                print("[INFO] Startup folder .bat not found (already removed or never registered).")
    except Exception as e:
        if verbose:
            print(f"[WARN] Could not remove Startup folder .bat: {e}")

    if verbose:
        print()
        print("✅  Done. JARVIS laptop client will no longer auto-start on login.")
        print("=" * 60)


def status(verbose: bool = True) -> bool:
    """
    Checks whether the auto-start entry currently exists.
    Returns True if registered, False otherwise.
    """
    _check_platform()

    import winreg

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _REGISTRY_KEY,
            0,
            winreg.KEY_READ,
        )
        value, _ = winreg.QueryValueEx(key, _ENTRY_NAME)
        winreg.CloseKey(key)
        if verbose:
            print(f"[REGISTERED] Auto-start is active.")
            print(f"             Command: {value}")
        return True
    except FileNotFoundError:
        if verbose:
            print("[NOT REGISTERED] Auto-start is not active.")
        return False
    except Exception as e:
        if verbose:
            print(f"[ERROR] Could not read registry: {e}")
        return False


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Register or remove JARVIS laptop client Windows auto-start entry.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deploy/register_autostart.py           # register auto-start
  python deploy/register_autostart.py --status  # check current status
  python deploy/register_autostart.py --remove  # remove auto-start
        """,
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove the auto-start entry instead of registering it.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print whether auto-start is currently registered.",
    )
    args = parser.parse_args()

    if args.status:
        status()
    elif args.remove:
        remove()
    else:
        register()
