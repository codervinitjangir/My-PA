"""
app/services/hardware_monitor.py — On-demand Hardware Monitoring

Exposes CPU%, RAM%, disk usage, and (where available) temperatures via:
  - GET /system/health  → JSON snapshot (called by frontend or Telegram /stats)
  - format_for_telegram() → human-readable string for Telegram /stats command

Design choices:
  * Pure psutil — already a project dependency, no new packages needed.
  * On-demand only — no background threads, no continuous alerts.
    This avoids notification spam and the "boy who cried wolf" problem.
  * Temperature is best-effort: it works on Linux and macOS via psutil.sensors_temperatures(),
    but returns an empty dict on Windows (psutil limitation — WMI not exposed).
    We degrade gracefully without crashing.
  * All public methods are synchronous (thread-safe, no async) so they can be
    called from both FastAPI route handlers and the Telegram bot handler.
"""

import logging
import platform
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("J.A.R.V.I.S.HardwareMonitor")

# psutil is a declared dependency — if absent, all methods return graceful errors
try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("[HARDWARE] psutil not installed. Run: pip install psutil")
    _PSUTIL_AVAILABLE = False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_bytes(b: int) -> str:
    """Formats a byte count into a human-readable string (GB preferred)."""
    gb = b / (1024 ** 3)
    if gb >= 1:
        return f"{gb:.1f} GB"
    mb = b / (1024 ** 2)
    return f"{mb:.0f} MB"


def _get_temperatures() -> Dict[str, float]:
    """
    Retrieves hardware temperatures via psutil.sensors_temperatures().

    Returns a flat dict of { label: celsius } or empty dict if unavailable.
    Windows always returns empty (psutil does not expose WMI sensors).
    Linux and macOS return coretemp / k10temp / acpitz etc. where present.
    """
    if not _PSUTIL_AVAILABLE:
        return {}
    try:
        raw = psutil.sensors_temperatures()
        if not raw:
            return {}

        temps: Dict[str, float] = {}
        for sensor_name, entries in raw.items():
            for entry in entries:
                label = entry.label or sensor_name
                # Deduplicate by prefixing with sensor name if label is generic
                key = f"{sensor_name}:{label}" if entry.label else sensor_name
                temps[key] = round(entry.current, 1)
        return temps
    except (AttributeError, Exception):
        return {}


def _get_disk_stats() -> list:
    """Returns a list of disk partition usage snapshots."""
    if not _PSUTIL_AVAILABLE:
        return []
    partitions = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total": _fmt_bytes(usage.total),
                "used": _fmt_bytes(usage.used),
                "free": _fmt_bytes(usage.free),
                "percent": usage.percent,
            })
        except PermissionError:
            # Some system mounts are not accessible on Windows
            continue
        except Exception:
            continue
    return partitions


# ── Main snapshot function ────────────────────────────────────────────────────

def get_hardware_snapshot() -> Dict[str, Any]:
    """
    Returns a comprehensive hardware health snapshot as a plain dict.

    Structure:
        {
          "ok": True,
          "captured_at": <epoch float>,
          "platform": "Windows / Linux / macOS",
          "cpu": { "percent": 23.4, "count_logical": 8, "count_physical": 4,
                   "freq_mhz": 2400 },
          "ram": { "total": "16.0 GB", "used": "9.2 GB", "free": "6.8 GB",
                   "percent": 57.5 },
          "swap": { "total": "8.0 GB", "used": "0.5 GB", "percent": 6.25 },
          "disk": [ { "device": "C:\\", "total": "512 GB", "percent": 68.0, ... } ],
          "temperatures": { "coretemp:Core 0": 51.0, "coretemp:Core 1": 49.0 },
          "uptime_hours": 12.4,
        }
    """
    if not _PSUTIL_AVAILABLE:
        return {
            "ok": False,
            "error": "psutil not installed — run: pip install psutil",
            "captured_at": time.time(),
        }

    try:
        # CPU — use interval=0.1 for a fast non-blocking sample
        cpu_pct = psutil.cpu_percent(interval=0.1)
        cpu_freq = psutil.cpu_freq()
        cpu_count_logical = psutil.cpu_count(logical=True) or 0
        cpu_count_physical = psutil.cpu_count(logical=False) or 0

        # RAM
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_hours = round(uptime_seconds / 3600, 1)

        snapshot = {
            "ok": True,
            "captured_at": time.time(),
            "platform": platform.system(),
            "cpu": {
                "percent": cpu_pct,
                "count_logical": cpu_count_logical,
                "count_physical": cpu_count_physical,
                "freq_mhz": round(cpu_freq.current) if cpu_freq else None,
            },
            "ram": {
                "total": _fmt_bytes(vm.total),
                "used": _fmt_bytes(vm.used),
                "free": _fmt_bytes(vm.available),
                "percent": vm.percent,
            },
            "swap": {
                "total": _fmt_bytes(swap.total),
                "used": _fmt_bytes(swap.used),
                "percent": swap.percent,
            },
            "disk": _get_disk_stats(),
            "temperatures": _get_temperatures(),
            "uptime_hours": uptime_hours,
        }

        logger.debug(
            "[HARDWARE] Snapshot: CPU=%.1f%% RAM=%.1f%% uptime=%.1fh",
            cpu_pct, vm.percent, uptime_hours
        )
        return snapshot

    except Exception as e:
        logger.error("[HARDWARE] Snapshot failed: %s", e)
        return {
            "ok": False,
            "error": str(e),
            "captured_at": time.time(),
        }


# ── Telegram-friendly formatter ───────────────────────────────────────────────

def format_for_telegram(snapshot: Optional[Dict[str, Any]] = None) -> str:
    """
    Returns a clean, emoji-annotated summary suitable for a Telegram message.

    Calls get_hardware_snapshot() if no snapshot is supplied.
    Keeps output under 500 chars for instant readability in Telegram.
    """
    if snapshot is None:
        snapshot = get_hardware_snapshot()

    if not snapshot.get("ok"):
        return f"⚠️ Hardware monitor unavailable: {snapshot.get('error', 'unknown error')}"

    cpu = snapshot["cpu"]
    ram = snapshot["ram"]
    swap = snapshot["swap"]
    disks = snapshot["disk"]
    temps = snapshot["temperatures"]
    uptime = snapshot.get("uptime_hours", "?")

    # CPU bar
    cpu_pct = cpu["percent"]
    cpu_bar = _progress_bar(cpu_pct)

    # RAM bar
    ram_pct = ram["percent"]
    ram_bar = _progress_bar(ram_pct)

    lines = [
        "🖥️  *System Health — J.A.R.V.I.S*",
        "",
        f"🔲 *CPU*  {cpu_bar} {cpu_pct:.1f}%",
        f"   {cpu['count_physical']}P/{cpu['count_logical']}L cores"
        + (f" @ {cpu['freq_mhz']} MHz" if cpu.get("freq_mhz") else ""),
        "",
        f"🧠 *RAM*  {ram_bar} {ram_pct:.1f}%",
        f"   {ram['used']} used / {ram['total']} total",
    ]

    # Swap — only show if used
    if swap["percent"] > 0.5:
        lines.append(f"💾 *Swap*  {swap['used']} / {swap['total']}  ({swap['percent']:.1f}%)")

    # Disks — show top 2 by percent to keep it short
    lines.append("")
    disk_shown = sorted(disks, key=lambda d: d["percent"], reverse=True)[:2]
    for d in disk_shown:
        disk_bar = _progress_bar(d["percent"])
        label = d["mountpoint"] if d["mountpoint"] != "/" else d["device"]
        lines.append(f"💿 *Disk* `{label}`  {disk_bar} {d['percent']:.1f}%")
        lines.append(f"   {d['used']} / {d['total']}")

    # Temperatures — show top 3 hottest
    if temps:
        lines.append("")
        lines.append("🌡️ *Temps*")
        sorted_temps = sorted(temps.items(), key=lambda kv: kv[1], reverse=True)[:3]
        for label, celsius in sorted_temps:
            heat_icon = "🔴" if celsius > 85 else "🟡" if celsius > 70 else "🟢"
            # Shorten label for telegram
            short_label = label.split(":")[-1][:20]
            lines.append(f"   {heat_icon} {short_label}: {celsius}°C")
    else:
        lines.append("")
        lines.append(f"🌡️ *Temps*: Not available ({snapshot['platform']})")

    lines.append("")
    lines.append(f"⏱️ Uptime: {uptime}h | Platform: {snapshot['platform']}")

    return "\n".join(lines)


def _progress_bar(percent: float, width: int = 8) -> str:
    """Builds a Unicode block progress bar. e.g. ██████░░ for 75%"""
    filled = int(round(percent / 100 * width))
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)
