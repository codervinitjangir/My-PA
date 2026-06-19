import threading
from typing import Optional, Tuple

_counter = 0
_lock = threading.Lock()


def get_next_key_pair(num_keys: int, need_brain: bool = True) -> Tuple[Optional[int], int]:
    """
    Thread-safe round-robin key rotation.
    Returns (brain_key_index, chat_key_index).
    If need_brain=False, brain index is None and chat index rotates normally.
    """
    global _counter

    if num_keys <= 0:
        return (None, 0)

    with _lock:
        idx = _counter % num_keys
        _counter += 1

    if not need_brain:
        return (None, idx)

    if num_keys == 1:
        return (0, 0)

    # Brain uses current slot, chat uses next slot — different keys for parallelism
    brain_idx = idx
    chat_idx = (idx + 1) % num_keys
    return (brain_idx, chat_idx)