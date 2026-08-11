"""Audio device discovery and selection.

Device *indices* are deliberately never persisted. Windows renumbers them when
hardware is plugged in or removed, so an index cached at startup can silently
point at the wrong device -- or a device that no longer exists -- the moment
headphones are connected. Configuration stores a name fragment instead, and it
is resolved to an index immediately before each use.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import sounddevice as sd

logger = logging.getLogger(__name__)


class AudioDeviceError(RuntimeError):
    """No usable audio device matched the request."""


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    """A resolved audio device."""

    index: int
    name: str
    channels: int
    default_samplerate: float

    def __str__(self) -> str:
        return f"[{self.index}] {self.name}"


def _describe(index: int, info: dict, kind: str) -> DeviceInfo:
    return DeviceInfo(
        index=index,
        name=str(info["name"]),
        channels=int(info[f"max_{kind}_channels"]),
        default_samplerate=float(info["default_samplerate"]),
    )


def list_devices(kind: str = "input") -> list[DeviceInfo]:
    """List devices that can be used for ``kind`` ('input' or 'output')."""
    return [
        _describe(index, info, kind)
        for index, info in enumerate(sd.query_devices())
        if int(info[f"max_{kind}_channels"]) > 0
    ]


def resolve_device(name_fragment: str | None, kind: str = "input") -> DeviceInfo:
    """Find the device to use, by name fragment or by falling back to default.

    Args:
        name_fragment: Case-insensitive substring of the device name. ``None``
            or empty selects the operating system default device.
        kind: Either ``'input'`` or ``'output'``.

    Returns:
        The matching device.

    Raises:
        AudioDeviceError: If no device matches, or if the system has none.
    """
    candidates = list_devices(kind)
    if not candidates:
        raise AudioDeviceError(f"No {kind} devices are available on this system")

    if name_fragment:
        needle = name_fragment.casefold()
        for device in candidates:
            if needle in device.name.casefold():
                logger.debug("Matched %s device %s for %r", kind, device, name_fragment)
                return device
        available = "\n  ".join(str(device) for device in candidates)
        raise AudioDeviceError(
            f"No {kind} device matches {name_fragment!r}. Available:\n  {available}"
        )

    default_index = sd.default.device[0 if kind == "input" else 1]
    if default_index is None or default_index < 0:
        return candidates[0]

    info = sd.query_devices(default_index)
    return _describe(int(default_index), info, kind)
