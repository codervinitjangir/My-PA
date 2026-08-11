"""Fetching the large files Bruno needs but does not ship.

The speech model and the voice are 200 MB between them. Bundling them into the
installer would work, but it makes every download of Bruno 200 MB heavier and
forces a fresh copy on people who already have one. Fetching them once, on
first run, keeps the installer small.

The cost of that choice is that first run now depends on the network, so this
module is built around the failure rather than the happy path:

* **Resume, always.** Every file downloads into a ``.part`` alongside its
  target and is renamed only when complete, so a partial file is never mistaken
  for a finished one. A retry sends ``Range`` and continues from what is
  already on disk.
* **Treat a stall as a failure.** A connection that stops delivering bytes but
  never closes will hang forever. The socket timeout turns that into an
  exception this can retry, which is the specific way a 700 MB download died
  twice on the machine Bruno was built on.
* **Report progress in bytes, not files.** One file is 141 MB and another is
  2 KB; counting files would show a progress bar that sits at zero and then
  jumps to done.
"""

from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from core import paths

logger = logging.getLogger(__name__)

HUGGINGFACE: Final = "https://huggingface.co"

# Bytes per read. Large enough that progress callbacks stay cheap, small enough
# that a cancelled download stops promptly rather than after the current chunk.
CHUNK_BYTES: Final = 1 << 18  # 256 KB

# Seconds without a single byte before the connection is considered dead.
# Generous, because a slow link is not a broken one -- this only has to catch
# a connection that has stopped entirely.
STALL_TIMEOUT_SECONDS: Final = 45.0

DEFAULT_ATTEMPTS: Final = 5
RETRY_BACKOFF_SECONDS: Final = 2.0

# CTranslate2 model repositories, keyed by the profile names in bruno.stt.whisper.
# Each holds the same four files.
WHISPER_REPOS: Final = {
    "tiny.en": "Systran/faster-whisper-tiny.en",
    "base.en": "Systran/faster-whisper-base.en",
    "small.en": "Systran/faster-whisper-small.en",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
}
WHISPER_FILES: Final = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")

# Approximate sizes, used only to show a total before any request has been made.
# Being wrong here costs a slightly inaccurate progress bar and nothing else.
_WHISPER_APPROX: Final = {
    "tiny.en": 75_000_000,
    "base.en": 148_000_000,
    "small.en": 484_000_000,
    "distil-large-v3": 1_510_000_000,
}

PIPER_VOICES: Final = {
    # Male, deeper first. A companion's voice is the single most noticeable
    # thing about it, so the catalogue is wide enough to choose by ear.
    "en_GB-alan-medium": "en/en_GB/alan/medium",
    "en_GB-northern_english_male-medium": "en/en_GB/northern_english_male/medium",
    "en_US-norman-medium": "en/en_US/norman/medium",
    "en_US-joe-medium": "en/en_US/joe/medium",
    "en_US-bryce-medium": "en/en_US/bryce/medium",
    "en_US-john-medium": "en/en_US/john/medium",
    "en_US-kusal-medium": "en/en_US/kusal/medium",
    "en_US-ryan-medium": "en/en_US/ryan/medium",
    "en_US-lessac-medium": "en/en_US/lessac/medium",
    # Female.
    "en_US-amy-medium": "en/en_US/amy/medium",
    "en_US-hfc_female-medium": "en/en_US/hfc_female/medium",
    "en_GB-alba-medium": "en/en_GB/alba/medium",
    "en_GB-cori-high": "en/en_GB/cori/high",
}
_VOICE_APPROX: Final = 64_000_000


class AssetError(RuntimeError):
    """A required file could not be downloaded."""


@dataclass(frozen=True, slots=True)
class Asset:
    """One file to fetch.

    Attributes:
        label: What to call this in a progress display. Shared by every file of
            a multi-file asset, so the user sees "speech model" rather than
            four filenames they have no reason to recognise.
        url: Where to fetch it from.
        target: Final location. Written atomically via a ``.part`` sibling.
        approx_bytes: Size estimate for the progress total, before the server
            has reported the real one.
    """

    label: str
    url: str
    target: Path
    approx_bytes: int = 0

    @property
    def is_installed(self) -> bool:
        """Whether the finished file is already on disk."""
        return self.target.is_file()

    @property
    def partial(self) -> Path:
        """The in-progress file, which may hold a resumable prefix."""
        return self.target.with_name(self.target.name + ".part")


@dataclass(frozen=True, slots=True)
class Progress:
    """A snapshot of an in-flight download, for a progress display.

    Attributes:
        label: The asset currently downloading.
        done_bytes: Bytes fetched across every asset in this run, including
            those resumed from a previous attempt.
        total_bytes: Best current estimate of the whole job.
    """

    label: str
    done_bytes: int
    total_bytes: int

    @property
    def fraction(self) -> float:
        """Completion in 0.0-1.0, clamped so an estimate cannot exceed one."""
        if self.total_bytes <= 0:
            return 0.0
        return min(1.0, self.done_bytes / self.total_bytes)


ProgressCallback = Callable[[Progress], None]
CancelCheck = Callable[[], bool]


# -- what Bruno needs ----------------------------------------------------------


def whisper_dir(model: str) -> Path:
    """Where a downloaded speech model lives."""
    return paths.models_dir() / model


def whisper_assets(model: str) -> list[Asset]:
    """Files making up one CTranslate2 speech model.

    Returns:
        The four files, or an empty list for a model Bruno has no repository for.
        An empty list means "let faster-whisper fetch this itself", which keeps
        an unrecognised model working instead of failing.
    """
    repo = WHISPER_REPOS.get(model)
    if repo is None:
        logger.debug("No download recipe for Whisper model %r", model)
        return []

    target_dir = whisper_dir(model)
    approx = _WHISPER_APPROX.get(model, 0)
    return [
        Asset(
            label="speech model",
            url=f"{HUGGINGFACE}/{repo}/resolve/main/{name}",
            target=target_dir / name,
            # The weights dominate; the other three are rounding error.
            approx_bytes=approx if name == "model.bin" else 0,
        )
        for name in WHISPER_FILES
    ]


def voice_assets(voice: str) -> list[Asset]:
    """The model and config making up one Piper voice.

    Raises:
        AssetError: If the voice name is not one Bruno knows how to fetch.
    """
    path = PIPER_VOICES.get(voice)
    if path is None:
        raise AssetError(
            f"Unknown voice {voice!r}. Known voices: {', '.join(sorted(PIPER_VOICES))}"
        )

    base = f"{HUGGINGFACE}/rhasspy/piper-voices/resolve/main/{path}/{voice}"
    target_dir = paths.voices_dir()
    return [
        Asset("voice", f"{base}.onnx", target_dir / f"{voice}.onnx", _VOICE_APPROX),
        Asset("voice", f"{base}.onnx.json", target_dir / f"{voice}.onnx.json"),
    ]


def required(*, model: str, voice: str) -> list[Asset]:
    """Everything Bruno needs before it can start, minus what is already present.

    Returns:
        The missing assets, in download order. Empty means Bruno is ready to run
        offline.
    """
    everything = whisper_assets(model) + voice_assets(voice)
    return [asset for asset in everything if not asset.is_installed]


# -- fetching ---------------------------------------------------------------


def install(
    assets: Sequence[Asset],
    *,
    on_progress: ProgressCallback | None = None,
    should_cancel: CancelCheck | None = None,
    attempts: int = DEFAULT_ATTEMPTS,
) -> None:
    """Download every asset, resuming and retrying as needed.

    Args:
        assets: What to fetch. Already-installed entries are skipped, so this
            is safe to call with a full list.
        on_progress: Called with a :class:`Progress` as bytes arrive. Runs on
            the calling thread and must be cheap.
        should_cancel: Polled between chunks. Returning True aborts, leaving
            ``.part`` files in place so a later attempt resumes.
        attempts: Tries per file before giving up.

    Raises:
        AssetError: If a file could not be fetched, or the run was cancelled.
    """
    pending = [asset for asset in assets if not asset.is_installed]
    if not pending:
        return

    total = sum(asset.approx_bytes for asset in pending)

    # Seeded with whatever an interrupted run left behind, *before* any request
    # is made. Counting these afterwards instead would open the progress bar at
    # zero and climb from there, which is indistinguishable from starting over
    # -- the download resumes correctly and the display says it did not.
    done = sum(item.partial.stat().st_size for item in pending if item.partial.is_file())
    total = max(total, done)

    if on_progress is not None:
        on_progress(Progress(pending[0].label, done, total))

    for asset in pending:
        def report(chunk: int, _asset: Asset = asset) -> None:
            # Nonlocal accumulation, so the bar reflects the whole job rather
            # than restarting at zero for each file.
            nonlocal done, total
            done += chunk
            # An estimate that turns out to be low would otherwise show a bar
            # stuck at 100% while bytes are still arriving.
            total = max(total, done)
            if on_progress is not None:
                on_progress(Progress(_asset.label, done, total))

        _fetch(asset, report, should_cancel, attempts)

    if on_progress is not None:
        on_progress(Progress("done", total, total))


def _fetch(
    asset: Asset,
    report: Callable[[int], None],
    should_cancel: CancelCheck | None,
    attempts: int,
) -> None:
    """Download one file, resuming across attempts."""
    asset.target.parent.mkdir(parents=True, exist_ok=True)
    already = asset.partial.stat().st_size if asset.partial.is_file() else 0
    if already:
        logger.info("Resuming %s from %.1f MB", asset.target.name, already / 1e6)

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            _fetch_once(asset, report, should_cancel)
        except _Cancelled:
            raise AssetError("Download cancelled") from None
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            last_error = exc
            offset = asset.partial.stat().st_size if asset.partial.is_file() else 0
            logger.warning(
                "Attempt %d/%d for %s failed at %.1f MB: %s",
                attempt,
                attempts,
                asset.target.name,
                offset / 1e6,
                exc,
            )
            if attempt < attempts:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
            continue
        else:
            # Renaming only now is what makes a truncated download impossible
            # to mistake for a complete one.
            asset.partial.replace(asset.target)
            logger.info("Installed %s", asset.target)
            return

    raise AssetError(
        f"Could not download {asset.target.name} after {attempts} attempts: {last_error}"
    ) from last_error


class _Cancelled(Exception):
    """Internal signal that ``should_cancel`` asked to stop."""


def _fetch_once(
    asset: Asset,
    report: Callable[[int], None],
    should_cancel: CancelCheck | None,
) -> None:
    """One download attempt, continuing from whatever ``.part`` already holds."""
    offset = asset.partial.stat().st_size if asset.partial.is_file() else 0

    request = urllib.request.Request(asset.url, headers={"User-Agent": "Bruno/1.0"})
    if offset:
        request.add_header("Range", f"bytes={offset}-")

    with urllib.request.urlopen(request, timeout=STALL_TIMEOUT_SECONDS) as response:
        # A server that ignores Range answers 200 with the whole file. Appending
        # that to what we have would corrupt it, so start over instead.
        resuming = response.status == 206
        if offset and not resuming:
            logger.info("Server ignored resume request; restarting %s", asset.target.name)
            # Give back the bytes already counted for this file, or the bar
            # would double-count them and sit at 100% while data still arrives.
            report(-offset)
            offset = 0

        mode = "ab" if resuming else "wb"
        with asset.partial.open(mode) as handle:
            while True:
                if should_cancel is not None and should_cancel():
                    raise _Cancelled
                chunk = response.read(CHUNK_BYTES)
                if not chunk:
                    break
                handle.write(chunk)
                report(len(chunk))


def clear_partials(assets: Iterable[Asset]) -> None:
    """Delete resumable fragments, forcing the next run to start clean.

    Only needed when a download is suspected of being corrupt, since a stalled
    transfer is normally worth resuming rather than discarding.
    """
    for asset in assets:
        try:
            asset.partial.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not delete %s", asset.partial, exc_info=True)
