"""
app/services/hardware_monitor.py — On-demand Hardware Monitoring

Exposes CPU%, RAM%, disk usage, GPU%, and (where available) temperatures via:
  - GET /system/health  → JSON snapshot (called by frontend or Telegram /stats)
  - format_for_telegram() → human-readable string for Telegram /stats command

Design choices:
  * Pure psutil + optional NVML/pynvml for GPU — no new mandatory dependencies.
  * GPU via pynvml first, NVML ctypes DLL fallback (zero subprocess, both paths).
    Adapted from Mark-L's system_monitor.py — best approach for cross-platform GPU.
  * On-demand snapshot: get_hardware_snapshot() — no background threads.
  * SystemMonitor class: stateful background alert monitor with configurable
    thresholds and cooldown logic (CPU streak guard to prevent false positives).
    Adopted from Mark-L's SystemMonitor pattern: 3 consecutive high CPU samples
    required before alert fires. 5-minute cooldown between same-type alerts.
  * Temperature on Windows via WMI if psutil returns empty (Mark-L pattern).
  * All public methods are synchronous so they work in both FastAPI and Telegram.
"""

import ctypes
import logging
import platform
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("J.A.R.V.I.S.HardwareMonitor")

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"

# psutil is a declared dependency — graceful if absent
try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("[HARDWARE] psutil not installed. Run: pip install psutil")
    _PSUTIL_AVAILABLE = False

# NVML DLL / library — cached after first successful load (Mark-L pattern)
_nvml_lib: Any = None
_nvml_ok: Optional[bool] = None   # None = untested, True = works, False = unavailable


# ── GPU via NVML ctypes (zero subprocess, cross-platform) ────────────────────

def _nvml_gpu_util() -> float:
    """
    GPU utilization % via NVML ctypes DLL — no subprocess, zero extra packages.

    Adapted from Mark-L system_monitor.py.  Tries Windows nvml.dll first,
    then Linux/macOS shared library paths.  Returns -1.0 if NVML unavailable.
    """
    global _nvml_lib, _nvml_ok
    if _nvml_ok is False:
        return -1.0

    try:
        class _Utilization(ctypes.Structure):
            _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

        if _nvml_lib is None:
            if _OS == "Windows":
                candidates = ("nvml", r"C:\Windows\System32\nvml.dll")
                _load = ctypes.WinDLL
            else:
                candidates = ("libnvidia-ml.so.1", "libnvidia-ml.so", "libnvidia-ml.dylib")
                _load = ctypes.CDLL

            for name in candidates:
                try:
                    lib = _load(name)
                    lib.nvmlInit_v2()
                    _nvml_lib = lib
                    logger.debug("[HARDWARE] NVML loaded via ctypes: %s", name)
                    break
                except Exception:
                    continue

        if _nvml_lib is None:
            _nvml_ok = False
            return -1.0

        dev = ctypes.c_void_p()
        _nvml_lib.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev))
        u = _Utilization()
        _nvml_lib.nvmlDeviceGetUtilizationRates(dev, ctypes.byref(u))
        _nvml_ok = True
        return float(u.gpu)

    except Exception:
        _nvml_ok = False
        return -1.0


def _get_gpu_usage() -> float:
    """
    GPU utilization % — tries pynvml first (if installed), then NVML ctypes.
    Returns -1.0 if no NVIDIA GPU or no driver.
    AMD GPU support is not available cross-platform without vendor SDKs.
    """
    # pynvml — subprocess-free, works everywhere if installed
    try:
        import pynvml  # type: ignore
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        gpu_pct = float(pynvml.nvmlDeviceGetUtilizationRates(h).gpu)
        logger.debug("[HARDWARE] GPU via pynvml: %.1f%%", gpu_pct)
        return gpu_pct
    except Exception:
        pass

    # Ctypes NVML fallback
    return _nvml_gpu_util()


# ── CPU temperature ───────────────────────────────────────────────────────────

def _get_cpu_temp() -> float:
    """
    CPU temperature in Celsius. Returns -1.0 if unavailable.

    Sources tried in order:
      1. psutil.sensors_temperatures() — Linux + macOS
      2. WMI MSAcpi_ThermalZoneTemperature — Windows only (optional wmi package)
    """
    if _PSUTIL_AVAILABLE:
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Known sensor names in priority order
                for name in ["coretemp", "k10temp", "cpu_thermal", "acpitz",
                             "cpu-thermal", "zenpower", "it8688"]:
                    if name in temps and temps[name]:
                        return temps[name][0].current
                # Fallback: first available sensor
                for entries in temps.values():
                    if entries:
                        return entries[0].current
        except Exception:
            pass

    # Windows WMI fallback (requires: pip install wmi)
    if _OS == "Windows":
        try:
            import wmi  # type: ignore
            w = wmi.WMI(namespace="root/wmi")
            tz = w.MSAcpi_ThermalZoneTemperature()
            if tz:
                return (tz[0].CurrentTemperature / 10.0) - 273.15
        except Exception:
            pass

    return -1.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_bytes(b: int) -> str:
    """Formats byte count into human-readable string."""
    gb = b / (1024 ** 3)
    if gb >= 1:
        return f"{gb:.1f} GB"
    mb = b / (1024 ** 2)
    return f"{mb:.0f} MB"


def _get_disk_stats() -> list:
    """Returns a list of disk partition usage snapshots."""
    if not _PSUTIL_AVAILABLE:
        return []
    partitions = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append({
                "device":     part.device,
                "mountpoint": part.mountpoint,
                "fstype":     part.fstype,
                "total":      _fmt_bytes(usage.total),
                "used":       _fmt_bytes(usage.used),
                "free":       _fmt_bytes(usage.free),
                "percent":    usage.percent,
            })
        except (PermissionError, Exception):
            continue
    return partitions


def _progress_bar(percent: float, width: int = 8) -> str:
    """Builds a Unicode block progress bar. e.g. ██████░░ for 75%"""
    filled = int(round(percent / 100 * width))
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


# ── Main snapshot ─────────────────────────────────────────────────────────────

def get_hardware_snapshot() -> Dict[str, Any]:
    """
    Returns a comprehensive hardware health snapshot as a plain dict.
    On-demand only — no background threads, no continuous alerts.

    Structure:
        {
          "ok": True,
          "captured_at": <epoch float>,
          "platform": "Windows / Linux / macOS",
          "cpu":  { "percent": 23.4, "count_logical": 8, "count_physical": 4,
                    "freq_mhz": 2400, "temp_c": 52.0 },
          "ram":  { "total": "16.0 GB", "used": "9.2 GB", "free": "6.8 GB",
                    "percent": 57.5 },
          "swap": { "total": "8.0 GB", "used": "0.5 GB", "percent": 6.25 },
          "gpu":  { "percent": 45.0 } or None if not available,
          "disk": [ { "device": "C:\\", "total": "512 GB", "percent": 68.0 } ],
          "temperatures": { "coretemp:Core 0": 51.0 },
          "uptime_hours": 12.4,
          "process_count": 220,
        }
    """
    if not _PSUTIL_AVAILABLE:
        return {
            "ok": False,
            "error": "psutil not installed — run: pip install psutil",
            "captured_at": time.time(),
        }

    try:
        cpu_pct = psutil.cpu_percent(interval=0.1)
        cpu_freq = psutil.cpu_freq()
        cpu_count_logical = psutil.cpu_count(logical=True) or 0
        cpu_count_physical = psutil.cpu_count(logical=False) or 0
        cpu_temp = _get_cpu_temp()

        vm   = psutil.virtual_memory()
        swap = psutil.swap_memory()

        boot_time = psutil.boot_time()
        uptime_hours = round((time.time() - boot_time) / 3600, 1)

        gpu_pct = _get_gpu_usage()

        # Build temp dict from psutil (full map) for the snapshot
        raw_temps: Dict[str, float] = {}
        try:
            if _PSUTIL_AVAILABLE:
                raw = psutil.sensors_temperatures()
                if raw:
                    for sensor_name, entries in raw.items():
                        for entry in entries:
                            label = entry.label or sensor_name
                            key = f"{sensor_name}:{label}" if entry.label else sensor_name
                            raw_temps[key] = round(entry.current, 1)
        except Exception:
            pass

        # If psutil temps empty and we have a WMI value, add it
        if not raw_temps and cpu_temp > 0:
            raw_temps["cpu_wmi"] = round(cpu_temp, 1)

        snapshot = {
            "ok":            True,
            "captured_at":   time.time(),
            "platform":      _OS,
            "cpu": {
                "percent":        cpu_pct,
                "count_logical":  cpu_count_logical,
                "count_physical": cpu_count_physical,
                "freq_mhz":       round(cpu_freq.current) if cpu_freq else None,
                "temp_c":         round(cpu_temp, 1) if cpu_temp > 0 else None,
            },
            "ram": {
                "total":   _fmt_bytes(vm.total),
                "used":    _fmt_bytes(vm.used),
                "free":    _fmt_bytes(vm.available),
                "percent": vm.percent,
            },
            "swap": {
                "total":   _fmt_bytes(swap.total),
                "used":    _fmt_bytes(swap.used),
                "percent": swap.percent,
            },
            "gpu":           {"percent": round(gpu_pct, 1)} if gpu_pct >= 0 else None,
            "disk":          _get_disk_stats(),
            "temperatures":  raw_temps,
            "uptime_hours":  uptime_hours,
            "process_count": len(psutil.pids()),
        }

        logger.debug(
            "[HARDWARE] Snapshot: CPU=%.1f%% RAM=%.1f%% GPU=%s uptime=%.1fh",
            cpu_pct, vm.percent,
            f"{gpu_pct:.1f}%" if gpu_pct >= 0 else "N/A",
            uptime_hours,
        )
        return snapshot

    except Exception as e:
        logger.error("[HARDWARE] Snapshot failed: %s", e)
        return {"ok": False, "error": str(e), "captured_at": time.time()}


# ── Stateful alert monitor (Mark-L SystemMonitor pattern) ─────────────────────

# Default alert thresholds — configurable per instance
DEFAULT_THRESHOLDS = {
    "cpu":  90.0,   # %
    "ram":  90.0,   # %
    "temp": 85.0,   # °C
    "gpu":  95.0,   # %
}

_ALERT_COOLDOWN_SECS = 300   # 5 minutes between same-type alerts
_CPU_STREAK_REQUIRED = 3     # CPU must be high for 3 consecutive checks (avoids false positives)


class SystemMonitor:
    """
    Stateful, threshold-based system monitor for background alert generation.

    Adopted from Mark-L's SystemMonitor class — adds streak logic (CPU must be
    above threshold for _CPU_STREAK_REQUIRED consecutive calls) and per-metric
    cooldown (5 minutes between same-category alerts).

    Usage:
        monitor = SystemMonitor()
        alert = monitor.check()   # call every 60s from a background thread
        if alert:
            send_to_user(alert)

    check() returns a [SYSTEM_ALERT] string (or None). The alert string is
    formatted as a prompt injection for the LLM so JARVIS can relay it
    naturally in the user's language.
    """

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._last_alert: Dict[str, float] = {}
        self._cpu_streak: int = 0

    def _cooldown_ok(self, key: str) -> bool:
        return (time.monotonic() - self._last_alert.get(key, 0.0)) > _ALERT_COOLDOWN_SECS

    def _record_alert(self, key: str) -> None:
        self._last_alert[key] = time.monotonic()

    def check(self) -> Optional[str]:
        """
        Samples current metrics and returns a [SYSTEM_ALERT] string if any
        threshold is breached after cooldown and streak requirements.

        Returns None if everything is within limits.
        Safe to call from any thread — psutil calls are thread-safe.
        """
        if not _PSUTIL_AVAILABLE:
            return None

        try:
            cpu_pct = psutil.cpu_percent(interval=None)
            ram_pct = psutil.virtual_memory().percent
            temp_c  = _get_cpu_temp()
            gpu_pct = _get_gpu_usage()
        except Exception:
            return None

        alerts: List[str] = []

        # CPU — streak guard: must be high for N consecutive samples
        if cpu_pct >= self.thresholds["cpu"]:
            self._cpu_streak += 1
            if self._cpu_streak >= _CPU_STREAK_REQUIRED and self._cooldown_ok("cpu"):
                alerts.append(
                    f"[SYSTEM_ALERT] CPU usage has been critically high ({cpu_pct:.0f}%) "
                    "for several consecutive checks. Warn the user in their language and "
                    "suggest closing heavy applications."
                )
                self._record_alert("cpu")
                self._cpu_streak = 0
        else:
            self._cpu_streak = 0

        # RAM
        if ram_pct >= self.thresholds["ram"] and self._cooldown_ok("ram"):
            alerts.append(
                f"[SYSTEM_ALERT] RAM is at {ram_pct:.0f}% — nearly exhausted. "
                "Warn the user in their language and suggest freeing memory."
            )
            self._record_alert("ram")

        # Temperature
        if temp_c > 0 and temp_c >= self.thresholds["temp"] and self._cooldown_ok("temp"):
            alerts.append(
                f"[SYSTEM_ALERT] CPU temperature is {temp_c:.0f}°C — above the safe limit. "
                "Warn the user in their language and advise reducing system load "
                "or checking cooling."
            )
            self._record_alert("temp")

        # GPU
        if gpu_pct >= 0 and gpu_pct >= self.thresholds["gpu"] and self._cooldown_ok("gpu"):
            alerts.append(
                f"[SYSTEM_ALERT] GPU load is at {gpu_pct:.0f}%. "
                "Briefly inform the user in their language."
            )
            self._record_alert("gpu")

        return " ".join(alerts) if alerts else None

    def get_status_dict(self) -> Dict[str, Any]:
        """Returns current raw metrics as a dict — same shape as get_hardware_snapshot()."""
        return get_hardware_snapshot()


# ── Telegram-friendly formatter ───────────────────────────────────────────────

def format_for_telegram(snapshot: Optional[Dict[str, Any]] = None) -> str:
    """
    Returns a clean, emoji-annotated summary suitable for a Telegram message.
    Calls get_hardware_snapshot() if no snapshot is supplied.
    """
    if snapshot is None:
        snapshot = get_hardware_snapshot()

    if not snapshot.get("ok"):
        return f"⚠️ Hardware monitor unavailable: {snapshot.get('error', 'unknown error')}"

    cpu   = snapshot["cpu"]
    ram   = snapshot["ram"]
    swap  = snapshot["swap"]
    disks = snapshot["disk"]
    temps = snapshot["temperatures"]
    gpu   = snapshot.get("gpu")
    uptime = snapshot.get("uptime_hours", "?")
    procs  = snapshot.get("process_count", "?")

    cpu_pct = cpu["percent"]
    ram_pct = ram["percent"]

    lines = [
        "🖥️  *System Health — J.A.R.V.I.S*",
        "",
        f"🔲 *CPU*  {_progress_bar(cpu_pct)} {cpu_pct:.1f}%",
        f"   {cpu['count_physical']}P/{cpu['count_logical']}L cores"
        + (f" @ {cpu['freq_mhz']} MHz" if cpu.get("freq_mhz") else ""),
    ]

    if cpu.get("temp_c"):
        heat = "🔴" if cpu["temp_c"] > 85 else "🟡" if cpu["temp_c"] > 70 else "🟢"
        lines.append(f"   {heat} {cpu['temp_c']}°C")

    lines += [
        "",
        f"🧠 *RAM*  {_progress_bar(ram_pct)} {ram_pct:.1f}%",
        f"   {ram['used']} used / {ram['total']} total",
    ]

    if swap["percent"] > 0.5:
        lines.append(f"💾 *Swap*  {swap['used']} / {swap['total']}  ({swap['percent']:.1f}%)")

    # GPU
    if gpu is not None:
        gpu_pct = gpu["percent"]
        lines += [
            "",
            f"🎮 *GPU*   {_progress_bar(gpu_pct)} {gpu_pct:.1f}%",
        ]

    # Disks
    lines.append("")
    disk_shown = sorted(disks, key=lambda d: d["percent"], reverse=True)[:2]
    for d in disk_shown:
        label = d["mountpoint"] if d["mountpoint"] != "/" else d["device"]
        lines.append(f"💿 *Disk* `{label}`  {_progress_bar(d['percent'])} {d['percent']:.1f}%")
        lines.append(f"   {d['used']} / {d['total']}")

    # Temperatures (non-WMI detailed ones from psutil)
    if temps and len(temps) > 1:  # more than just the WMI fallback
        lines.append("")
        lines.append("🌡️ *Temps*")
        sorted_temps = sorted(temps.items(), key=lambda kv: kv[1], reverse=True)[:3]
        for label, celsius in sorted_temps:
            if label == "cpu_wmi":
                continue  # already shown in CPU line
            heat = "🔴" if celsius > 85 else "🟡" if celsius > 70 else "🟢"
            short = label.split(":")[-1][:20]
            lines.append(f"   {heat} {short}: {celsius}°C")
    elif not temps:
        lines += ["", f"🌡️ *Temps*: N/A ({snapshot['platform']})"]

    lines += [
        "",
        f"⏱️ Uptime: {uptime}h  |  🔢 Processes: {procs}  |  📱 {snapshot['platform']}",
    ]

    return "\n".join(lines)
