"""Speech-to-text using faster-whisper.

Hardware is detected at runtime rather than configured. Bruno is meant to be
downloaded and run by people whose machines we know nothing about, so the
engine picks a model that suits what it finds:

===========  ==================  ==========  ============================
Hardware     Model               Precision   Typical latency for 3s audio
===========  ==================  ==========  ============================
NVIDIA GPU   distil-large-v3     float16     ~250 ms
CPU only     base.en             int8        ~600 ms
===========  ==================  ==========  ============================

Two behaviours exist purely to protect the first interaction. Loading a model
takes 5-20 seconds, so it happens in the background at startup rather than on
the user's first press. And CUDA compiles kernels on first use, making that
inference several times slower than every later one, so a throwaway pass over
silence absorbs the cost before anyone is waiting on it.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np

from voice.audio.recorder import SAMPLE_RATE, AudioClip
from core import assets, paths
from core.protocols import Transcript
from voice.stt import runtime

# Must precede the faster_whisper import: it registers the CUDA DLL search
# path and works around PyAV being unloadable under code-integrity policies.
runtime.prepare()

import ctranslate2  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402

logger = logging.getLogger(__name__)

WARMUP_SECONDS: Final = 0.5

# Whisper has never seen Bruno's name and reliably hears "Eevee". A short prompt
# biases the decoder toward expected vocabulary. Keep it minimal: long prompts
# leak into transcripts and encourage the model to invent matching text.
NAME_PROMPT: Final = "Bruno"


@dataclass(frozen=True, slots=True)
class ModelProfile:
    """A model paired with the hardware settings it should run under."""

    name: str
    device: str
    compute_type: str

    def __str__(self) -> str:
        return f"{self.name} on {self.device} ({self.compute_type})"


GPU_PROFILE: Final = ModelProfile("distil-large-v3", "cuda", "float16")
CPU_PROFILE: Final = ModelProfile("base.en", "cpu", "int8")


def default_cpu_threads() -> int:
    """Pick a thread count for CPU inference.

    Measured on an 8-core/16-thread Ryzen 7 5800H: the library default was
    ~880 ms per utterance, 12 threads ~665 ms, and all 16 logical cores ~760 ms.
    Saturating every hyperthread makes things worse, because the matrix
    kernels contend for shared execution units rather than gaining parallelism.
    Three quarters of the logical cores tracked the measured optimum and leaves
    headroom for the audio callback, which must not be starved.
    """
    logical = os.cpu_count() or 4
    return max(4, logical * 3 // 4)


def detect_profile(preference: str = "auto") -> ModelProfile:
    """Choose a model profile for the current machine.

    Args:
        preference: ``auto``, ``cpu``, or ``cuda``. ``cuda`` is honoured even
            when the probe below finds nothing, so a system-wide CUDA install
            can still be used.

    Returns:
        The profile to load.
    """
    if preference == "cpu":
        return CPU_PROFILE
    if preference == "cuda":
        return GPU_PROFILE
    if preference != "auto":
        logger.warning("Unknown BRUNO_DEVICE=%r; using auto detection", preference)

    # Both conditions are required. A CUDA device without the cuDNN runtime
    # loads nothing, and discovering that *after* fetching 1.5 GB of GPU-sized
    # weights is a poor first-run experience.
    try:
        if ctranslate2.get_cuda_device_count() > 0 and runtime.has_cuda_runtime():
            return GPU_PROFILE
    except Exception:  # noqa: BLE001 -- a broken CUDA install must not be fatal
        logger.warning("CUDA probe failed; using CPU", exc_info=True)
    return CPU_PROFILE


class WhisperTranscriber:
    """Transcribes microphone audio. Satisfies :class:`~bruno.core.protocols.STTEngine`.

    Args:
        profile: Explicit model and hardware settings, bypassing detection.
        device_preference: ``auto``, ``cpu``, or ``cuda``. Ignored when
            ``profile`` is given.
        model_dir: Where weights are cached. ``None`` resolves at load time,
            which matters for packaged builds: the location depends on whether
            Bruno is frozen, and capturing it at import time would bake in a
            temporary directory that no longer exists on the next run.
        beam_size: Decoding beam width. Five is both more accurate and, in
            practice, no slower than greedy decoding here -- see ``vad_filter``.
        vad_filter: Drop silence before inference. This is the single most
            valuable setting in the class. Whisper hallucinates confident
            sentences over silence ("Thank you very much.") and then loops on
            them, and measured on real recordings that pushed the worst-case
            latency to 7.4 s against a 0.8 s median. With silence removed the
            worst case falls to 0.78 s, and clips containing no speech return
            in single-digit milliseconds instead of hundreds.
        language: Forced language code, or ``None`` to auto-detect. Forcing it
            skips a detection pass and avoids Bruno occasionally deciding that a
            mumbled English sentence was Welsh.
        initial_prompt: Vocabulary hint prepended to the decoder context, or
            ``None`` to disable. See :data:`NAME_PROMPT`.
        cpu_threads: Threads for CPU inference. Zero picks a value from the
            core count; see :func:`default_cpu_threads`.
    """

    def __init__(
        self,
        *,
        profile: ModelProfile | None = None,
        device_preference: str = "auto",
        model_dir: Path | None = None,
        beam_size: int = 5,
        language: str | None = "en",
        vad_filter: bool = True,
        initial_prompt: str | None = NAME_PROMPT,
        cpu_threads: int = 0,
    ) -> None:
        self._profile = profile or detect_profile(device_preference)
        self._model_dir = model_dir or paths.models_dir()
        self._beam_size = beam_size
        self._language = language
        self._vad_filter = vad_filter
        self._initial_prompt = initial_prompt
        self._cpu_threads = cpu_threads or default_cpu_threads()

        self._model: WhisperModel | None = None
        self._ready = threading.Event()
        self._load_lock = threading.Lock()
        self._load_error: Exception | None = None

    # -- lifecycle ----------------------------------------------------------

    @property
    def profile(self) -> ModelProfile:
        """The model and hardware in use."""
        return self._profile

    @property
    def is_ready(self) -> bool:
        """Whether the model is loaded and warmed up."""
        return self._ready.is_set()

    def load(self) -> None:
        """Download if needed, load the model, and warm it up.

        Blocks for several seconds. Idempotent.

        Raises:
            RuntimeError: If the model could not be loaded.
        """
        with self._load_lock:
            if self._model is not None:
                return

            self._model_dir.mkdir(parents=True, exist_ok=True)
            started = time.perf_counter()

            try:
                model = self._load_profile(self._profile)
            except Exception as gpu_error:
                if self._profile.device != "cuda":
                    self._load_error = gpu_error
                    raise RuntimeError(
                        f"Could not load {self._profile}: {gpu_error}"
                    ) from gpu_error

                # A CUDA *device* being present does not mean the cuDNN and
                # cuBLAS runtimes are installed. Detection cannot tell the
                # difference, so the real proof is a load attempt: fall back
                # rather than leaving the user with a stack trace.
                logger.warning(
                    "GPU inference unavailable (%s); falling back to %s",
                    gpu_error,
                    CPU_PROFILE,
                )
                try:
                    model = self._load_profile(CPU_PROFILE)
                except Exception as cpu_error:
                    self._load_error = cpu_error
                    raise RuntimeError(
                        f"Could not load {self._profile} or {CPU_PROFILE}: {cpu_error}"
                    ) from cpu_error
                self._profile = CPU_PROFILE

            self._model = model
            elapsed = time.perf_counter() - started
            logger.info("Model loaded in %.1fs; warming up", elapsed)

            self._warm_up()
            self._ready.set()

    def _load_profile(self, profile: ModelProfile) -> WhisperModel:
        """Instantiate one profile, downloading the weights only if it must.

        Prefers a directory Bruno downloaded itself, which is what a packaged
        install always has: setup fetches the weights up front so that model
        loading is a local operation with no network path through it. Falling
        back to the model *name* lets faster-whisper fetch from the Hub, which
        is how a source checkout with no prior setup still works.
        """
        local = assets.whisper_dir(profile.name)
        source = str(local) if (local / "model.bin").is_file() else profile.name
        logger.info("Loading %s from %s", profile, source)

        return WhisperModel(
            source,
            device=profile.device,
            compute_type=profile.compute_type,
            download_root=str(self._model_dir),
            cpu_threads=self._cpu_threads,
        )

    def load_async(self) -> threading.Thread:
        """Load the model on a background thread.

        Returns:
            The loader thread, already started.
        """
        thread = threading.Thread(target=self._load_quietly, name="ev-stt-load", daemon=True)
        thread.start()
        return thread

    def wait_until_ready(self, timeout: float | None = None) -> bool:
        """Block until the model is usable.

        Args:
            timeout: Seconds to wait, or ``None`` to wait indefinitely.

        Returns:
            True if the model is ready.

        Raises:
            RuntimeError: If background loading failed.
        """
        ready = self._ready.wait(timeout)
        if self._load_error is not None:
            raise RuntimeError(f"Model loading failed: {self._load_error}") from self._load_error
        return ready

    def _load_quietly(self) -> None:
        try:
            self.load()
        except Exception:  # noqa: BLE001 -- surfaced through wait_until_ready
            logger.exception("Background model load failed")

    def _warm_up(self) -> None:
        """Run one throwaway inference so the first real request is fast.

        Uses faint noise rather than digital silence: some builds short-circuit
        on an all-zero signal, which would skip the kernel compilation this
        exists to trigger.
        """
        rng = np.random.default_rng(seed=0)
        noise = rng.normal(0.0, 1e-4, int(SAMPLE_RATE * WARMUP_SECONDS)).astype(np.float32)

        started = time.perf_counter()
        try:
            self._run(noise)
        except Exception:  # noqa: BLE001 -- warm-up is an optimisation, not a requirement
            logger.warning("Warm-up pass failed; first request may be slow", exc_info=True)
            return
        logger.info("Warm-up took %.2fs", time.perf_counter() - started)

    # -- inference ----------------------------------------------------------

    def transcribe(self, clip: AudioClip) -> Transcript:
        """Transcribe a recording.

        Args:
            clip: Audio from the recorder, at 16 kHz mono float32.

        Returns:
            The transcript. ``text`` is empty when no speech was recognised.

        Raises:
            RuntimeError: If called before the model has loaded.
        """
        if self._model is None:
            raise RuntimeError("Transcriber is not loaded; call load() first")

        started = time.perf_counter()
        text, language = self._run(clip.samples)
        latency = time.perf_counter() - started

        logger.debug(
            "Transcribed %.2fs of audio in %.2fs (%.1fx realtime)",
            clip.duration,
            latency,
            clip.duration / latency if latency else 0.0,
        )
        return Transcript(text=text, language=language, latency=latency)

    def _run(self, samples: np.ndarray) -> tuple[str, str]:
        """Execute the model and flatten its segment stream into one string."""
        assert self._model is not None

        segments, info = self._model.transcribe(
            samples,
            beam_size=self._beam_size,
            language=self._language,
            vad_filter=self._vad_filter,
            initial_prompt=self._initial_prompt,
            # Whisper conditions on its own previous output by default, which
            # on short clips can send it into repetition loops.
            condition_on_previous_text=False,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text, info.language
