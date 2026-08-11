"""Driving the browser the user already has open.

Automation frameworks were the obvious choice and the wrong one. Playwright
and Selenium drive a *fresh* browser: no logins, no history, none of the tabs
already open. "Go back" then has nowhere to go back to, and "search for this"
lands in a window the user is not looking at. Chrome's debugging protocol is
closer, but requires Chrome to be started with a special flag, which means
closing the browser the user is already using.

So Bruno types. Opening a page hands a URL to the default browser exactly as
clicking a link does; navigation synthesises the keystrokes a person would
press. Two consequences worth stating plainly:

**Bruno acts on the focused window and never steals focus.** Windows restricts
which processes may raise a window, and fighting that produces something that
works on one machine and not the next. Acting on what is already in front of
the user is both simpler and more predictable -- when someone says "scroll
down", the thing they mean is the thing they are looking at.

**Which is why the foreground window is checked first.** Sending Page Down to
whatever happens to be focused would eventually page through someone's editor
or, worse, their terminal. If the front window is not a browser, Bruno says so
rather than pressing keys into it.
"""

from __future__ import annotations

import logging
import subprocess
import time
import urllib.parse
import webbrowser
from typing import Any, Final

from core.protocols import ToolResult
from input import win32
from tools.registry import Tool

logger = logging.getLogger(__name__)

SEARCH_URL: Final = "https://www.google.com/search?q={query}"

# Identified by executable, not by window class. Every Electron application
# reports Chrome's window class -- Visual Studio Code among them -- so a check
# based on class alone cheerfully classifies a code editor as a browser and
# sends Page Down into somebody's source file.
BROWSER_PROCESSES: Final = frozenset(
    {
        "chrome.exe",
        "msedge.exe",
        "firefox.exe",
        "brave.exe",
        "opera.exe",
        "opera_gx.exe",
        "vivaldi.exe",
        "arc.exe",
        "zen.exe",
        "librewolf.exe",
        "waterfox.exe",
        "iexplore.exe",
    }
)

# Time for a newly launched browser to come up before Bruno claims success.
LAUNCH_SETTLE_SECONDS: Final = 0.6

# Pause between repeated keystrokes, so a page has a moment to scroll rather
# than receiving three Page Downs as one jump.
REPEAT_GAP_SECONDS: Final = 0.12
MAX_REPEATS: Final = 10


class BrowserError(RuntimeError):
    """The browser could not be driven."""


# -- what the browser can be told to do -------------------------------------

# Each action is the keystroke a person would press. The names are the whole
# interface the model sees: they appear in the parameter's enum, and are
# deliberately self-explanatory so the description does not have to repeat them.
# It used to, which cost two hundred and fifty tokens on every single request
# for information the enum already carried.
ACTIONS: Final[dict[str, tuple[int, ...]]] = {
    "scroll_down": (win32.VK_NEXT,),
    "scroll_up": (win32.VK_PRIOR,),
    "top": (win32.VK_HOME,),
    "bottom": (win32.VK_END,),
    "back": (win32.VK_MENU, win32.VK_LEFT),
    "forward": (win32.VK_MENU, win32.VK_RIGHT),
    "reload": (win32.VK_F5,),
    "new_tab": (win32.VK_CONTROL, ord("T")),
    "close_tab": (win32.VK_CONTROL, ord("W")),
    "reopen_tab": (win32.VK_CONTROL, win32.VK_LSHIFT, ord("T")),
    "next_tab": (win32.VK_CONTROL, win32.VK_TAB),
    "find": (win32.VK_CONTROL, ord("F")),
}


def is_browser_focused() -> tuple[bool, str]:
    """Whether the front window is a browser.

    Returns:
        A ``(is_browser, description)`` pair. The description names whatever
        is actually in front, so a refusal can say what it saw rather than
        just declining.
    """
    hwnd = win32.foreground_window()
    if not hwnd:
        return False, "nothing"

    title = win32.window_title(hwnd)
    executable = win32.process_name(win32.window_process_id(hwnd))
    described = title or executable or "an unknown window"

    if executable in BROWSER_PROCESSES:
        return True, described

    logger.debug("Foreground window is %s (%s), not a browser", described, executable)
    return False, described


def open_url(url: str) -> None:
    """Open a URL in the user's default browser.

    Raises:
        BrowserError: If no browser could be launched.
    """
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        opened = webbrowser.open(url, new=2)
    except (OSError, webbrowser.Error) as exc:
        raise BrowserError(f"Could not open the browser: {exc}") from exc

    if not opened:
        # webbrowser returns False when it found nothing to launch. Falling
        # back to the shell handles machines where no browser is registered
        # the way Python expects but one is still installed.
        try:
            subprocess.run(["cmd", "/c", "start", "", url], check=True, shell=False)
        except (OSError, subprocess.SubprocessError) as exc:
            raise BrowserError(f"Could not open the browser: {exc}") from exc

    time.sleep(LAUNCH_SETTLE_SECONDS)


def press(action: str, times: int = 1) -> None:
    """Send the keystroke for one action.

    Raises:
        BrowserError: If the action is unknown or Windows refused the input.
    """
    keys = ACTIONS.get(action)
    if keys is None:
        raise BrowserError(f"I don't know how to {action.replace('_', ' ')}.")

    for index in range(max(1, min(times, MAX_REPEATS))):
        if index:
            time.sleep(REPEAT_GAP_SECONDS)
        if not win32.send_keys(*keys):
            raise BrowserError(
                "Windows would not let me send that keystroke. The window in "
                "front may be running as administrator."
            )


# -- tools ------------------------------------------------------------------


def _run_open(arguments: dict[str, Any]) -> ToolResult:
    # "url" and "query" are accepted as well as "target" because models were
    # asked for those names in an earlier version and still reach for them.
    target = str(
        arguments.get("target") or arguments.get("url") or arguments.get("query") or ""
    ).strip()
    if not target:
        return ToolResult("I need a website or something to search for.")

    # A bare word is a search; anything with a dot and no spaces is an address.
    looks_like_address = "." in target and " " not in target
    url = target if looks_like_address else SEARCH_URL.format(
        query=urllib.parse.quote_plus(target)
    )

    try:
        open_url(url)
    except BrowserError as exc:
        return ToolResult(str(exc))

    logger.info("Opened %s", url)
    if looks_like_address:
        return ToolResult(f"Opened {target} in the browser.")
    return ToolResult(f"Searched the web for {target!r} in the browser.")


def _run_control(arguments: dict[str, Any]) -> ToolResult:
    action = str(arguments.get("action", "")).strip().lower()
    try:
        times = int(arguments.get("times", 1))
    except (TypeError, ValueError):
        times = 1

    if action not in ACTIONS:
        known = ", ".join(sorted(ACTIONS))
        return ToolResult(f"{action!r} is not something I can do. I know: {known}.")

    focused, what = is_browser_focused()
    if not focused:
        # Refusing loudly beats paging through someone's editor.
        return ToolResult(
            f"The browser is not the window in front -- I can see {what}. "
            "Tell the user to click the browser first, in your own words."
        )

    try:
        press(action, times)
    except BrowserError as exc:
        return ToolResult(str(exc))

    logger.info("Sent %s x%d to %s", action, times, what)
    return ToolResult(f"Done: {action.replace('_', ' ')}.")


def open_tool() -> Tool:
    """Opening a site or running a web search."""
    return Tool(
        name="open_in_browser",
        description=(
            "Open a website or search the web: open a site, go to a page, "
            "search for something, look something up. Opens a page but does "
            "not read it; use look_at_screen after if you need to know what "
            "appeared."
        ),
        # One required parameter, not two optional ones. A schema where every
        # property is optional gives the decoder nothing it must produce, and
        # Groq was observed emitting the tool name and its arguments fused into
        # a single string -- rejected by its own validator, after which Bruno said
        # nothing at all. An address and a search phrase are told apart in
        # code, which is a job for code rather than for a model.
        parameters={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": (
                        "A web address such as youtube.com, or what to search "
                        "the web for"
                    ),
                }
            },
            "required": ["target"],
        },
        run=_run_open,
    )


def control_tool() -> Tool:
    """Scrolling and navigating the page already open."""
    return Tool(
        name="control_browser",
        description=(
            "Scroll or navigate the page the user is already looking at. Acts "
            "on whichever browser window is in front. Does not click links or "
            "buttons."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": sorted(ACTIONS)},
                # No minimum or maximum. Groq builds a decoding grammar from
                # this schema and cannot express numeric bounds: including them
                # made every tool call fail outright with "Failed to call a
                # function". The range is enforced in press() instead, which is
                # where it belongs -- a model is not a validator.
                "times": {"type": "integer", "description": f"Repeat count, 1 to {MAX_REPEATS}"},
            },
            "required": ["action"],
        },
        run=_run_control,
    )
