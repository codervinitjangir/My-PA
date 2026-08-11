"""Import-time environment fixes required before faster-whisper will load.

Both workarounds here are Windows-specific and must run *before* anything
imports ``faster_whisper``, which is why they live in their own module rather
than at the top of the transcriber.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from types import ModuleType

logger = logging.getLogger(__name__)


def register_cuda_libraries() -> list[Path]:
    """Make pip-installed NVIDIA runtime DLLs discoverable.

    ``nvidia-cudnn-cu12`` and ``nvidia-cublas-cu12`` drop their DLLs inside
    site-packages, which is not on the Windows loader search path. Since Python
    3.8, adding a directory to ``PATH`` is no longer enough -- extension modules
    only see directories registered through ``os.add_dll_directory``. Without
    this, CUDA inference fails at runtime with an opaque "cannot load cudnn"
    error, and ctranslate2 falls back to the CPU with no explanation.

    Returns:
        The directories that were registered.
    """
    if sys.platform != "win32":
        return []

    try:
        import nvidia
    except ImportError:
        logger.debug("NVIDIA runtime packages not installed; CPU inference only")
        return []

    registered: list[Path] = []
    for namespace_root in nvidia.__path__:
        for bin_dir in sorted(Path(namespace_root).glob("*/bin")):
            if not bin_dir.is_dir():
                continue
            try:
                os.add_dll_directory(str(bin_dir))
            except OSError:
                logger.warning("Could not register DLL directory %s", bin_dir)
                continue
            registered.append(bin_dir)

    logger.debug("Registered %d CUDA DLL director(ies)", len(registered))
    return registered


def stub_pyav_if_unavailable() -> bool:
    """Neutralise faster-whisper's hard dependency on PyAV.

    ``faster_whisper/__init__.py`` imports PyAV so that ``decode_audio`` can
    read audio *files*. Bruno never uses that path: recordings arrive as numpy
    arrays straight from the microphone, which ``transcribe`` accepts directly.

    PyAV ships unsigned DLLs, so on machines with Smart App Control or a WDAC
    policy enabled the import fails and takes faster-whisper down with it. This
    installs a placeholder module so the import succeeds. Any genuine attempt
    to use PyAV raises with an explanatory message rather than an obscure
    attribute error.

    Returns:
        True if a stub was installed, False if the real PyAV works.
    """
    try:
        import av  # noqa: F401
    except Exception as exc:  # noqa: BLE001 -- DLL policy blocks raise ImportError subclasses and OSError
        logger.info("PyAV unavailable (%s); installing stub for file decoding", exc)
    else:
        return False

    def _unavailable(name: str) -> None:
        raise RuntimeError(
            "PyAV is not usable in this environment, so audio *file* decoding "
            f"is unavailable (attribute {name!r}). Bruno transcribes numpy arrays "
            "from the microphone and does not need it."
        )

    stub = ModuleType("av")
    stub.__getattr__ = _unavailable  # type: ignore[method-assign]
    sys.modules["av"] = stub
    return True


_cuda_lib_dirs: list[Path] = []


def has_cuda_runtime() -> bool:
    """Whether the cuDNN and cuBLAS libraries needed for GPU inference exist.

    A CUDA-capable *device* is not sufficient: ctranslate2 also needs the cuDNN
    and cuBLAS runtimes, which ship separately. Checking this before selecting
    a model matters because the failure would otherwise surface only after
    downloading gigabytes of GPU-sized weights.

    Only pip-installed NVIDIA packages are detected. A system-wide CUDA
    installation still works, but must be selected explicitly with
    ``BRUNO_DEVICE=cuda``.
    """
    return bool(_cuda_lib_dirs)


def prepare() -> None:
    """Apply every environment fix. Safe to call more than once."""
    global _cuda_lib_dirs
    _cuda_lib_dirs = register_cuda_libraries()
    stub_pyav_if_unavailable()
