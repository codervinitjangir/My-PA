"""Fetch everything Bruno needs to run: the Piper binary, a voice, and the speech model.

Run from the repository root::

    python -m scripts.setup                          # default voice and model
    python -m scripts.setup --voice en_US-lessac-medium
    python -m scripts.setup --list                   # show known voices
    python -m scripts.setup --where                  # print resolved paths

Downloads land in git-ignored directories and resume if interrupted, so
re-running this after a dropped connection continues rather than restarting.

This is the developer-facing version of what the packaged build does silently
on first run; both go through :mod:`bruno.core.assets`.
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Final

from core import assets, paths
from core import logging as jarvis_logging
from core.config import load_settings

# The binary ships inside the installer rather than downloading, so this exists
# only to populate a source checkout.
PIPER_URL: Final = (
    "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/"
    "piper_windows_amd64.zip"
)


class _Reporter:
    """Prints one self-overwriting progress line, throttled to stay readable."""

    def __init__(self, interval: float = 0.2) -> None:
        self._interval = interval
        self._last = 0.0

    def __call__(self, progress: assets.Progress) -> None:
        now = time.monotonic()
        if progress.label != "done" and now - self._last < self._interval:
            return
        self._last = now

        filled = int(progress.fraction * 24)
        bar = "#" * filled + "." * (24 - filled)
        print(
            f"\r  [{bar}] {progress.fraction:>4.0%}  "
            f"{progress.done_bytes / 1e6:.0f} / {progress.total_bytes / 1e6:.0f} MB  "
            f"{progress.label:<14}",
            end="",
            flush=True,
        )
        if progress.label == "done":
            print()


def install_piper() -> None:
    """Download and extract the Piper binary into ``vendor/``."""
    binary = paths.piper_binary()
    if binary.is_file():
        print(f"Piper already installed at {binary}")
        return

    vendor = binary.parent.parent
    vendor.mkdir(parents=True, exist_ok=True)
    archive = vendor / "piper_windows_amd64.zip"

    print("Downloading Piper...")
    urllib.request.urlretrieve(PIPER_URL, archive)
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(vendor)
    archive.unlink()

    if not binary.is_file():
        raise SystemExit(f"Extraction did not produce {binary}")
    print(f"Installed {binary}")


def install_assets(model: str, voice: str) -> None:
    """Download the speech model and voice, skipping what is already present."""
    missing = assets.required(model=model, voice=voice)
    if not missing:
        print(f"Speech model {model} and voice {voice} already installed")
        return

    approx = sum(item.approx_bytes for item in missing) / 1e6
    resumable = sum(
        item.partial.stat().st_size for item in missing if item.partial.is_file()
    )
    print(f"Downloading {len(missing)} file(s), about {approx:.0f} MB...")
    if resumable:
        print(f"  {resumable / 1e6:.0f} MB already downloaded; continuing from there.")

    assets.install(missing, on_progress=_Reporter())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", default="", help="voice to install")
    parser.add_argument("--model", default="", help="Whisper model to install")
    parser.add_argument("--list", action="store_true", help="list known voices and exit")
    parser.add_argument("--where", action="store_true", help="print resolved paths and exit")
    args = parser.parse_args()

    # Without this the "Resuming ... from N MB" line never reaches the terminal,
    # which is what made a working resume look like a fresh download.
    jarvis_logging.configure(level="INFO", quiet_libraries=True, to_file=False)

    if args.where:
        print(paths.describe())
        return 0

    if args.list:
        print("Known voices:")
        for name in sorted(assets.PIPER_VOICES):
            installed = " (installed)" if (paths.voices_dir() / f"{name}.onnx").is_file() else ""
            print(f"  {name}{installed}")
        return 0

    settings = load_settings()
    voice = args.voice or settings.voice
    # Import here so --list and --where work without loading ctranslate2.
    from voice.stt.whisper import detect_profile

    model = args.model or detect_profile(settings.device).name

    install_piper()
    try:
        install_assets(model, voice)
    except assets.AssetError as exc:
        print(f"\nSetup failed: {exc}")
        print("Run this again to resume from where it stopped.")
        return 1

    print("\nDone. Set JARVIS_VOICE in .env to choose between installed voices.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
