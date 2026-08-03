"""
app/services/reminder_service.py — OS-Native Smart Reminders

Rewritten from Mark-L's actions/reminder.py in our codebase style.

Key difference from our old APScheduler approach:
  Reminders are registered with the OS scheduler — NOT held in-process.
  They SURVIVE JARVIS restarts (process kills, deployments, reboots).

How it works:
  1. Writes a self-deleting Python notification script to ~/.jarvis/reminders/
  2. Registers it with the platform scheduler:
       Windows → Windows Task Scheduler (schtasks via XML)
       macOS   → LaunchAgent plist (launchctl load)
       Linux   → systemd-run (transient timer) or 'at' fallback
  3. The script fires at the set time, shows a system notification via
     multiple fallbacks (plyer → win10toast → winsound/osascript/notify-send),
     then deletes itself.

Platform coverage:
  - Windows: Task Scheduler (built-in on all Windows versions)
  - macOS:   LaunchAgents (built-in, no extra packages)
  - Linux:   systemd-run (most modern distros) or 'at' (legacy)

Security:
  - Message is sanitised (no shell injection chars)
  - Script is written with chmod 600 (owner read/write only)
  - Script self-deletes after firing — no lingering scripts

Usage:
  from app.services.reminder_service import set_reminder
  result = set_reminder(date_str="2026-08-05", time_str="09:00",
                        message="Stand-up in 5 minutes")
  # → "Reminder set for August 05 at 09:00 AM."
"""

import json
import logging
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("J.A.R.V.I.S.Reminder")

_OS = platform.system()   # "Windows" | "Darwin" | "Linux"

# Suppress console windows on Windows subprocess calls
_WIN_HIDE: dict = (
    {"creationflags": subprocess.CREATE_NO_WINDOW}
    if _OS == "Windows" else {}
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _scripts_dir() -> Path:
    """Returns the directory where reminder scripts are stored."""
    d = Path.home() / ".jarvis" / "reminders"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sanitise(text: str, max_len: int = 200) -> str:
    """Removes shell-injection chars and truncates."""
    return (
        text.replace("\\", "")
            .replace('"', "")
            .replace("'", "")
            .replace("\n", " ")
            .replace("\r", "")
            .strip()
    )[:max_len]


def _get_pythonw() -> Path:
    """
    Returns pythonw.exe on Windows (no console window),
    or sys.executable on other platforms.
    """
    python_exe = Path(sys.executable)
    if _OS == "Windows":
        pythonw = python_exe.parent / "pythonw.exe"
        if pythonw.exists():
            return pythonw
    return python_exe


# ── Notification script writer ─────────────────────────────────────────────────

def _write_notify_script(task_name: str, message: str) -> Path:
    """
    Writes a self-deleting Python notification script for the target OS.
    The script tries multiple notification backends in order of preference.
    """
    script_path = _scripts_dir() / f"{task_name}.py"
    msg_literal = json.dumps(message)   # safe JSON-encoded string literal

    if _OS == "Windows":
        notify_block = f"""
message = {msg_literal}
notified = False

try:
    from plyer import notification
    notification.notify(title="J.A.R.V.I.S Reminder", message=message, timeout=15)
    notified = True
except Exception:
    pass

if not notified:
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast("J.A.R.V.I.S Reminder", message, duration=15, threaded=False)
        notified = True
    except Exception:
        pass

if not notified:
    try:
        import subprocess
        subprocess.run(["msg", "*", "/TIME:30", message], check=False)
    except Exception:
        pass

try:
    import winsound
    for freq in [800, 1000, 1200]:
        winsound.Beep(freq, 180)
        import time; time.sleep(0.08)
except Exception:
    pass
"""

    elif _OS == "Darwin":
        notify_block = f"""
message = {msg_literal}
notified = False

try:
    from plyer import notification
    notification.notify(title="J.A.R.V.I.S Reminder", message=message, timeout=15)
    notified = True
except Exception:
    pass

if not notified:
    try:
        import subprocess
        script = 'display notification "{{}}" with title "J.A.R.V.I.S Reminder"'.format(
            message.replace('"', '')
        )
        subprocess.run(["osascript", "-e", script], check=False)
    except Exception:
        pass
"""

    else:  # Linux
        notify_block = f"""
message = {msg_literal}
notified = False

try:
    from plyer import notification
    notification.notify(title="J.A.R.V.I.S Reminder", message=message, timeout=15)
    notified = True
except Exception:
    pass

if not notified:
    try:
        import subprocess
        subprocess.run(
            ["notify-send", "--urgency=normal", "--expire-time=15000",
             "J.A.R.V.I.S Reminder", message],
            check=False
        )
    except Exception:
        pass
"""

    script_body = f"""# Auto-generated by J.A.R.V.I.S reminder — do not edit
import sys, os, pathlib
{notify_block}
# Self-delete after firing
try:
    pathlib.Path(__file__).unlink(missing_ok=True)
except Exception:
    pass
"""
    script_path.write_text(script_body, encoding="utf-8")
    script_path.chmod(0o600)   # owner read/write only
    return script_path


# ── Platform schedulers ───────────────────────────────────────────────────────

def _schedule_windows(target_dt: datetime, task_name: str, script_path: Path) -> bool:
    """
    Registers a Windows Task Scheduler task via XML.
    Uses pythonw.exe (no console window). Self-contained — no external deps.
    Returns True on success.
    """
    python_exe = _get_pythonw()
    xml_path   = _scripts_dir() / f"{task_name}.xml"

    xml_content = (
        '<?xml version="1.0" encoding="UTF-16"?>\n'
        '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
        '  <RegistrationInfo><Description>J.A.R.V.I.S Reminder</Description></RegistrationInfo>\n'
        '  <Triggers><TimeTrigger>\n'
        f'    <StartBoundary>{target_dt.strftime("%Y-%m-%dT%H:%M:%S")}</StartBoundary>\n'
        '    <Enabled>true</Enabled>\n'
        '  </TimeTrigger></Triggers>\n'
        '  <Actions><Exec>\n'
        f'    <Command>{python_exe}</Command>\n'
        f'    <Arguments>"{script_path}"</Arguments>\n'
        '  </Exec></Actions>\n'
        '  <Settings>\n'
        '    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n'
        '    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n'
        '    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n'
        '    <StartWhenAvailable>true</StartWhenAvailable>\n'
        '    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>\n'
        '    <Enabled>true</Enabled>\n'
        '  </Settings>\n'
        '  <Principals><Principal>\n'
        '    <LogonType>InteractiveToken</LogonType>\n'
        '    <RunLevel>LeastPrivilege</RunLevel>\n'
        '  </Principal></Principals>\n'
        '</Task>'
    )

    xml_path.write_text(xml_content, encoding="utf-16")

    result = subprocess.run(
        ["schtasks", "/Create", "/TN", task_name, "/XML", str(xml_path), "/F"],
        capture_output=True, text=True, **_WIN_HIDE,
    )

    # Always clean up the temp XML
    try:
        xml_path.unlink(missing_ok=True)
    except Exception:
        pass

    if result.returncode != 0:
        err = (result.stderr or result.stdout).strip()
        logger.error("[REMINDER] schtasks failed: %s", err)
        return False

    logger.info("[REMINDER] Task Scheduler registered: %s at %s", task_name, target_dt)
    return True


def _schedule_macos(target_dt: datetime, task_name: str, script_path: Path) -> bool:
    """Registers a macOS LaunchAgent plist for one-shot execution."""
    agents_dir = Path.home() / "Library" / "LaunchAgents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    label     = f"com.jarvis.reminder.{task_name}"
    plist_path = agents_dir / f"{label}.plist"

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>             <string>{label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{sys.executable}</string>
    <string>{script_path}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Year</key>   <integer>{target_dt.year}</integer>
    <key>Month</key>  <integer>{target_dt.month}</integer>
    <key>Day</key>    <integer>{target_dt.day}</integer>
    <key>Hour</key>   <integer>{target_dt.hour}</integer>
    <key>Minute</key> <integer>{target_dt.minute}</integer>
  </dict>
  <key>RunAtLoad</key>         <false/>
  <key>StandardOutPath</key>   <string>/dev/null</string>
  <key>StandardErrorPath</key> <string>/dev/null</string>
</dict>
</plist>
"""
    plist_path.write_text(plist, encoding="utf-8")
    plist_path.chmod(0o644)

    result = subprocess.run(
        ["launchctl", "load", str(plist_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        plist_path.unlink(missing_ok=True)
        script_path.unlink(missing_ok=True)
        logger.error("[REMINDER] launchctl failed: %s", result.stderr.strip())
        return False

    logger.info("[REMINDER] LaunchAgent registered: %s", label)
    return True


def _schedule_linux(target_dt: datetime, task_name: str, script_path: Path) -> bool:
    """
    Linux: tries systemd-run first (most modern distros), then 'at' as fallback.
    """
    if shutil.which("systemd-run"):
        on_calendar = target_dt.strftime("%Y-%m-%d %H:%M:00")
        result = subprocess.run(
            [
                "systemd-run", "--user",
                f"--on-calendar={on_calendar}",
                f"--unit={task_name}",
                "--",
                sys.executable, str(script_path),
            ],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            logger.info("[REMINDER] systemd-run registered: %s", task_name)
            return True
        logger.debug("[REMINDER] systemd-run failed, trying 'at': %s", result.stderr.strip())

    if shutil.which("at"):
        at_time = target_dt.strftime("%H:%M %Y-%m-%d")
        cmd_str = f"{sys.executable} {script_path}\n"
        result = subprocess.run(
            ["at", at_time],
            input=cmd_str, capture_output=True, text=True,
        )
        if result.returncode == 0:
            logger.info("[REMINDER] 'at' registered: %s", task_name)
            return True
        logger.error("[REMINDER] 'at' failed: %s", result.stderr.strip())
        return False

    logger.error("[REMINDER] Neither systemd-run nor 'at' found on this Linux system.")
    return False


# ── Public entry point ────────────────────────────────────────────────────────

def set_reminder(
    date_str: str,
    time_str: str,
    message: str = "Reminder",
) -> str:
    """
    Sets an OS-native reminder that survives JARVIS restarts.

    Args:
        date_str: "YYYY-MM-DD"
        time_str: "HH:MM" (24h)
        message:  Human-readable reminder text

    Returns:
        A human-readable confirmation string, or an error description.
    """
    date_str = (date_str or "").strip()
    time_str = (time_str or "").strip()
    message  = (message  or "Reminder").strip()

    if not date_str or not time_str:
        return "I need both a date and a time to set a reminder."

    try:
        target_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        return "I couldn't parse that date or time. Please use YYYY-MM-DD and HH:MM."

    if target_dt <= datetime.now():
        return "That time has already passed — I can't set a reminder in the past."

    safe_msg  = _sanitise(message)
    task_name = f"JARVISReminder_{target_dt.strftime('%Y%m%d_%H%M%S')}"

    try:
        script_path = _write_notify_script(task_name, safe_msg)
    except Exception as e:
        logger.error("[REMINDER] Could not write script: %s", e)
        return f"Could not prepare the reminder script: {e}"

    try:
        if _OS == "Windows":
            ok = _schedule_windows(target_dt, task_name, script_path)
        elif _OS == "Darwin":
            ok = _schedule_macos(target_dt, task_name, script_path)
        else:
            ok = _schedule_linux(target_dt, task_name, script_path)
    except Exception as e:
        try:
            script_path.unlink(missing_ok=True)
        except Exception:
            pass
        logger.error("[REMINDER] Scheduling exception: %s", e)
        return "Something went wrong while scheduling the reminder."

    if not ok:
        try:
            script_path.unlink(missing_ok=True)
        except Exception:
            pass
        return "I couldn't register the reminder with the system scheduler."

    friendly = target_dt.strftime("%B %d at %I:%M %p")
    return f"✅ Reminder set for {friendly}.\nI'll notify you even if JARVIS isn't running."


def parse_and_set_reminder(raw: str) -> str:
    """
    Convenience parser for natural-ish Telegram command input.
    Expected format: /remind YYYY-MM-DD HH:MM Your reminder text
    Returns the same string as set_reminder().
    """
    parts = raw.strip().split(None, 2)
    if len(parts) < 2:
        return (
            "Usage: /remind YYYY-MM-DD HH:MM Your message\n"
            "Example: /remind 2026-08-05 09:00 Stand-up in 5 minutes"
        )

    date_str = parts[0]
    time_str = parts[1] if len(parts) > 1 else ""
    message  = parts[2] if len(parts) > 2 else "Reminder"

    return set_reminder(date_str=date_str, time_str=time_str, message=message)
