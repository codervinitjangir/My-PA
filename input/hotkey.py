"""Global hotkeys backed by a Win32 low-level keyboard hook.

``RegisterHotKey`` is the obvious API for a global shortcut but is unusable
here for two reasons: it reports key-*down* only, so press-and-hold is
impossible, and it cannot stop Alt+Space from opening the window system menu.
A ``WH_KEYBOARD_LL`` hook gives us both the key-up edge and the ability to
swallow a keystroke before any application sees it.

One hook serves every binding. Chords are matched on the *exact* set of
modifiers held, so Ctrl+Alt+Space and Alt+Space stay distinct rather than the
second firing whenever the first is pressed.

Threading model, which matters more than it looks::

    OS input thread          dispatcher thread        caller's thread
    ---------------          -----------------        ---------------
    _hook_procedure()        _dispatch_loop()         start() / stop()
      classify key             pop from queue
      push to queue            invoke handler
      return immediately

Windows unhooks a low-level hook that exceeds ``LowLevelHooksTimeout``
(300 ms by default) and reports no error -- the hotkey simply stops working.
So the hook procedure only classifies and enqueues; handlers, which will
eventually start audio capture, run elsewhere.
"""

from __future__ import annotations

import ctypes
import logging
import queue
import threading
from collections.abc import Callable
from ctypes import wintypes as wt
from dataclasses import dataclass
from enum import Enum, auto
from typing import Final

from input import win32

logger = logging.getLogger(__name__)

_SUPPRESS_EVENT: Final = 1
_SHUTDOWN_SENTINEL: Final = None
_STOP_TIMEOUT_SECONDS: Final = 2.0


class Modifier(Enum):
    """Modifier keys a chord can require."""

    ALT = auto()
    CTRL = auto()
    SHIFT = auto()


_MODIFIER_KEYS: Final = {
    win32.VK_LMENU: Modifier.ALT,
    win32.VK_RMENU: Modifier.ALT,
    win32.VK_LCONTROL: Modifier.CTRL,
    win32.VK_RCONTROL: Modifier.CTRL,
    win32.VK_LSHIFT: Modifier.SHIFT,
    win32.VK_RSHIFT: Modifier.SHIFT,
}


class Edge(Enum):
    """Which end of a keypress a handler is for."""

    PRESSED = auto()
    RELEASED = auto()


@dataclass(frozen=True, slots=True)
class Chord:
    """A key plus the exact set of modifiers that must be held."""

    key: int
    modifiers: frozenset[Modifier]

    def __str__(self) -> str:
        order = [Modifier.CTRL, Modifier.ALT, Modifier.SHIFT]
        names = [m.name.title() for m in order if m in self.modifiers]
        return "+".join([*names, f"0x{self.key:02X}"])


@dataclass(slots=True)
class Binding:
    """Handlers for one chord."""

    on_press: Callable[[], None]
    on_release: Callable[[], None] | None = None


ALT_SPACE: Final = Chord(win32.VK_SPACE, frozenset({Modifier.ALT}))
CTRL_ALT_SPACE: Final = Chord(
    win32.VK_SPACE, frozenset({Modifier.CTRL, Modifier.ALT})
)


class HotkeyListener:
    """Dispatches handlers for registered chords.

    Args:
        suppress: Hide matched chords from other applications. Leaving this on
            is what stops Windows opening its system menu on Alt+Space.
    """

    def __init__(self, *, suppress: bool = True) -> None:
        self._suppress = suppress
        self._bindings: dict[Chord, Binding] = {}

        self._held: set[Modifier] = set()
        self._active: Chord | None = None

        self._hook_handle: int | None = None
        self._pump_thread_id: int | None = None
        self._pump_thread: threading.Thread | None = None
        self._dispatch_thread: threading.Thread | None = None
        self._events: queue.Queue[tuple[Chord, Edge] | None] = queue.Queue()
        self._ready = threading.Event()
        self._install_error: OSError | None = None

        # Windows holds only a raw pointer to the callback. Without a Python
        # reference the trampoline is garbage collected and the next keystroke
        # crashes the interpreter, so bind it to the instance for its lifetime.
        self._hook_proc = win32.HOOKPROC(self._hook_procedure)

    # -- registration -------------------------------------------------------

    def register(
        self,
        chord: Chord,
        on_press: Callable[[], None],
        on_release: Callable[[], None] | None = None,
    ) -> None:
        """Bind handlers to a chord.

        Args:
            chord: Key and modifiers to match exactly.
            on_press: Called when the chord engages.
            on_release: Called when the key is released. Omit for chords that
                act on press alone, such as a toggle.
        """
        self._bindings[chord] = Binding(on_press=on_press, on_release=on_release)
        logger.debug("Registered %s", chord)

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Install the hook and begin dispatching.

        Raises:
            OSError: If Windows refuses to install the hook.
            RuntimeError: If already running.
        """
        if self._pump_thread is not None:
            raise RuntimeError("Hotkey listener is already running")

        self._install_error = None
        self._ready.clear()

        self._dispatch_thread = threading.Thread(
            target=self._dispatch_loop, name="ev-hotkey-dispatch", daemon=True
        )
        self._dispatch_thread.start()

        self._pump_thread = threading.Thread(
            target=self._pump_loop, name="ev-hotkey-pump", daemon=True
        )
        self._pump_thread.start()

        self._ready.wait()
        if self._install_error is not None:
            self.stop()
            raise self._install_error

        logger.info(
            "Hotkeys active: %s", ", ".join(str(c) for c in self._bindings) or "none"
        )

    def stop(self) -> None:
        """Uninstall the hook and stop both worker threads."""
        if self._pump_thread_id is not None:
            win32.user32.PostThreadMessageW(self._pump_thread_id, win32.WM_QUIT, 0, 0)

        if self._pump_thread is not None:
            self._pump_thread.join(timeout=_STOP_TIMEOUT_SECONDS)
            self._pump_thread = None

        self._events.put(_SHUTDOWN_SENTINEL)
        if self._dispatch_thread is not None:
            self._dispatch_thread.join(timeout=_STOP_TIMEOUT_SECONDS)
            self._dispatch_thread = None

        self._pump_thread_id = None
        self._held.clear()
        self._active = None
        logger.info("Hotkeys stopped")

    def __enter__(self) -> HotkeyListener:
        self.start()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.stop()

    # -- OS input thread ----------------------------------------------------

    def _pump_loop(self) -> None:
        """Install the hook, then run a message loop to keep it serviced.

        A low-level hook is bound to the thread that installed it and is only
        delivered while that thread pumps messages, so installation and the
        loop must live together here rather than in ``start``.
        """
        self._pump_thread_id = win32.kernel32.GetCurrentThreadId()

        handle = win32.user32.SetWindowsHookExW(
            win32.WH_KEYBOARD_LL, self._hook_proc, None, 0
        )
        if not handle:
            self._install_error = ctypes.WinError(ctypes.get_last_error())
            self._ready.set()
            return

        self._hook_handle = handle
        self._ready.set()

        message = wt.MSG()
        while win32.user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            win32.user32.TranslateMessage(ctypes.byref(message))
            win32.user32.DispatchMessageW(ctypes.byref(message))

        win32.user32.UnhookWindowsHookEx(self._hook_handle)
        self._hook_handle = None

    def _hook_procedure(self, code: int, wparam: int, lparam: int) -> int:
        """Raw hook entry point. Must return promptly -- see module docstring."""
        if code != win32.HC_ACTION:
            return win32.user32.CallNextHookEx(None, code, wparam, lparam)

        event = ctypes.cast(lparam, ctypes.POINTER(win32.KBDLLHOOKSTRUCT)).contents

        # Bruno synthesises keystrokes to drive the browser, and its own hook sees
        # them exactly as if they had been typed. Alt+Left to go back would
        # otherwise register Alt as held, so the next Space would fire
        # push-to-talk -- Bruno interrupting itself with a key it pressed. Passing
        # injected events straight through also means Bruno cannot be driven by
        # another program's synthetic input.
        if event.flags & win32.LLKHF_INJECTED:
            return win32.user32.CallNextHookEx(None, code, wparam, lparam)

        try:
            handled = self._classify(event.vkCode, wparam)
        except Exception:  # noqa: BLE001 -- never let an exception kill the hook
            logger.exception("Hotkey classification failed; passing key through")
            handled = False

        if handled and self._suppress:
            return _SUPPRESS_EVENT
        return win32.user32.CallNextHookEx(None, code, wparam, lparam)

    def _classify(self, vk_code: int, message: int) -> bool:
        """Update chord state for one key event.

        Returns:
            True if Bruno owns this keystroke and it should be hidden from other
            applications.
        """
        is_down = message in win32.KEY_DOWN_MESSAGES
        is_up = message in win32.KEY_UP_MESSAGES

        modifier = _MODIFIER_KEYS.get(vk_code)
        if modifier is not None:
            if is_down:
                self._held.add(modifier)
            elif is_up:
                self._held.discard(modifier)
            # Modifiers are never suppressed: doing so would break every other
            # shortcut on the system.
            return False

        if is_down:
            return self._on_key_down(vk_code)
        if is_up:
            return self._on_key_up(vk_code)
        return False

    def _on_key_down(self, vk_code: int) -> bool:
        if self._active is not None:
            # Auto-repeat while held. Swallow it, but do not re-fire.
            return self._active.key == vk_code

        chord = Chord(vk_code, frozenset(self._held))
        if chord not in self._bindings:
            return False

        self._active = chord
        self._events.put((chord, Edge.PRESSED))
        return True

    def _on_key_up(self, vk_code: int) -> bool:
        active = self._active
        if active is None or active.key != vk_code:
            return False

        self._active = None
        if self._bindings[active].on_release is not None:
            self._events.put((active, Edge.RELEASED))
        # Suppressed regardless: we swallowed the matching key-down, so
        # releasing it must not leak a keystroke into the focused window.
        return True

    # -- dispatcher thread --------------------------------------------------

    def _dispatch_loop(self) -> None:
        """Run handlers off the OS input thread."""
        while True:
            event = self._events.get()
            if event is _SHUTDOWN_SENTINEL:
                return

            chord, edge = event
            binding = self._bindings.get(chord)
            if binding is None:
                continue

            handler = binding.on_press if edge is Edge.PRESSED else binding.on_release
            if handler is None:
                continue

            try:
                handler()
            except Exception:  # noqa: BLE001 -- one bad handler must not end the loop
                logger.exception("Handler for %s %s raised", chord, edge.name)
