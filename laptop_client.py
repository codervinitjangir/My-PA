"""
laptop_client.py — J.A.R.V.I.S Local Relay Client

Connects to the JARVIS server via WebSocket and handles local commands:
  open_app, open_url, screenshot, keyboard_shortcut, type_text, scroll

Clipboard Intelligence (opt-in):
  Set CLIPBOARD_INTELLIGENCE_ENABLED=true in .env to enable.
  When clipboard content changes and contains >20 characters, a desktop
  notification offers to Translate / Summarize / Explain the text via JARVIS.
  Off by default — clipboard monitoring is a real privacy consideration.
  Enable only if you want JARVIS to be aware of what you copy.
"""

import asyncio
import os
import io
import base64
import json
import logging
import threading
import time
import webbrowser
import websockets
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="[LAPTOP] %(message)s")
logger = logging.getLogger()

load_dotenv()

JARVIS_API_TOKEN = os.getenv("JARVIS_API_TOKEN", "").strip()
JARVIS_BASE_URL = os.getenv("JARVIS_SERVER_URL", "http://127.0.0.1:8000").rstrip("/")

# Replace with your actual Render URL
RENDER_URL = f"ws://127.0.0.1:8000/laptop/ws"

if JARVIS_API_TOKEN:
    RENDER_URL += f"?token={JARVIS_API_TOKEN}"

# ── Clipboard Intelligence (opt-in) ─────────────────────────────────────────
# Default OFF — user must explicitly set CLIPBOARD_INTELLIGENCE_ENABLED=true
_CLIPBOARD_ENABLED = os.getenv("CLIPBOARD_INTELLIGENCE_ENABLED", "false").strip().lower() == "true"
_CLIPBOARD_MIN_LENGTH = 20   # chars — ignore short copies (URLs, filenames, etc.)
_CLIPBOARD_POLL_INTERVAL = 1.5  # seconds between clipboard checks


def _send_clipboard_to_jarvis(text: str, action: str) -> None:
    """
    Sends the clipboard text to JARVIS's chat endpoint for the requested action.
    Runs in a daemon thread — fire-and-forget, does not block.

    action: one of "translate", "summarize", "explain"
    """
    import urllib.request
    import urllib.error

    prompts = {
        "translate":  f"Translate the following text to English (if not already English) and respond with only the translation:\n\n{text}",
        "summarize":  f"Summarize the following text in 2-3 sentences:\n\n{text}",
        "explain":    f"Explain the following text simply and clearly:\n\n{text}",
    }
    prompt = prompts.get(action, f"What does this mean: {text}")

    payload = json.dumps({
        "message": prompt,
        "session_id": "clipboard_intelligence",
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if JARVIS_API_TOKEN:
        headers["Authorization"] = f"Bearer {JARVIS_API_TOKEN}"

    url = f"{JARVIS_BASE_URL}/chat"
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            response_text = result.get("response", result.get("message", str(result)))
            logger.info("[CLIPBOARD] JARVIS response: %s", response_text[:200])
            # Show response as another desktop notification
            _show_notification("J.A.R.V.I.S", response_text[:200])
    except Exception as e:
        logger.warning("[CLIPBOARD] JARVIS request failed: %s", e)


def _show_notification(title: str, message: str) -> None:
    """
    Shows a desktop notification on Windows.

    Uses win10toast if installed; degrades to a console print if not.
    win10toast is lightweight and optional — it is NOT a hard dependency.
    Install with: pip install win10toast
    """
    try:
        from win10toast import ToastNotifier
        notifier = ToastNotifier()
        notifier.show_toast(title, message[:250], duration=8, threaded=True)
    except ImportError:
        # Fallback — print visually distinct alert to console
        print(f"\n{'='*50}")
        print(f"  {title}")
        print(f"  {message}")
        print(f"{'='*50}\n")
    except Exception as e:
        logger.debug("[CLIPBOARD] Toast notification failed: %s", e)


def _offer_clipboard_action(text: str) -> None:
    """
    Shows a notification offering clipboard actions.

    On Windows, the toast is informational only (no interactive buttons
    in win10toast). The user replies via Telegram or the JARVIS chat UI.
    For a future enhancement, this could send a Telegram message with
    inline buttons for direct selection.
    """
    preview = text[:60].replace("\n", " ")
    if len(text) > 60:
        preview += "…"

    # Offer the 3 actions — since toast buttons are not cross-platform,
    # we automatically perform all three asynchronously and let the user
    # read the one that's useful to them. This is the simplest UX that
    # works without UI framework dependencies.
    message = (
        f"Clipboard captured ({len(text)} chars). Analyzing...\n"
        f"Preview: {preview}"
    )
    _show_notification("J.A.R.V.I.S — Clipboard Intelligence", message)
    logger.info("[CLIPBOARD] Offering analysis for %d-char text", len(text))

    # Run JARVIS action in background — won't block the monitor loop
    # Default to summarize (most universally useful for long copied text)
    threading.Thread(
        target=_send_clipboard_to_jarvis,
        args=(text, "summarize"),
        daemon=True,
        name="clipboard-jarvis",
    ).start()


def _clipboard_monitor_loop() -> None:
    """
    Background daemon thread that polls the clipboard every 1.5 seconds.
    Fires only when:
      1. Content has actually changed since last check
      2. Content length > _CLIPBOARD_MIN_LENGTH
      3. Content is plain text (not an image or file path only)

    Uses pyperclip for cross-platform clipboard access.
    pyperclip is already used elsewhere in the project.
    """
    try:
        import pyperclip
    except ImportError:
        logger.warning(
            "[CLIPBOARD] pyperclip not installed — clipboard intelligence disabled. "
            "Run: pip install pyperclip"
        )
        return

    logger.info(
        "[CLIPBOARD] Intelligence ENABLED — monitoring clipboard "
        "(min %d chars, poll %.1fs)",
        _CLIPBOARD_MIN_LENGTH,
        _CLIPBOARD_POLL_INTERVAL,
    )

    last_content: str = ""
    try:
        last_content = pyperclip.paste() or ""
    except Exception as e:
        logger.debug("[CLIPBOARD] Initial paste failed: %s", e)

    while True:
        try:
            time.sleep(_CLIPBOARD_POLL_INTERVAL)
            current = pyperclip.paste() or ""

            # Skip if unchanged or below minimum length
            if current == last_content:
                continue
            last_content = current

            stripped = current.strip()
            if len(stripped) < _CLIPBOARD_MIN_LENGTH:
                continue

            # Basic filter: skip pure file paths and URLs (not interesting to analyze)
            is_url = stripped.startswith(("http://", "https://", "ftp://"))
            is_path = (len(stripped) < 300 and (stripped.startswith(("C:\\", "D:\\", "/")) or "\\" in stripped))
            if is_url or is_path:
                logger.debug("[CLIPBOARD] Skipping URL/path: %.50s", stripped)
                continue

            _offer_clipboard_action(stripped)

        except Exception as e:
            logger.debug("[CLIPBOARD] Monitor error (will retry): %s", e)


# ── Command Handler ──────────────────────────────────────────────────────────

async def handle_command(command: dict) -> dict:
    """Execute local command based on action."""
    action = command.get("action")
    payload = command.get("payload", {})
    
    if action == "open_app":
        target = payload.get("target")
        if target:
            try:
                os.startfile(target)
                return {"status": "success", "message": f"Opened {target}"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "No target provided"}
        
    elif action == "open_url":
        url = payload.get("url")
        if url:
            try:
                webbrowser.open(url)
                return {"status": "success", "message": f"Opened URL {url}"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "No URL provided"}
        
    elif action in ("screenshot", "capture_screen"):
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            raw_bytes = buf.getvalue()
            buf.close()
            img.close()
            b64 = base64.b64encode(raw_bytes).decode("utf-8")
            return {"status": "success", "image_b64": b64}
        except ImportError:
            return {"status": "error", "message": "Pillow is not installed. Run pip install Pillow"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    elif action == "lock_screen":
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return {"status": "success", "message": "Screen locked"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
            
    elif action == "keyboard_shortcut":
        shortcut = payload.get("shortcut")
        if shortcut:
            try:
                import keyboard
                keyboard.send(shortcut)
                return {"status": "success", "message": f"Pressed {shortcut}"}
            except ImportError:
                return {"status": "error", "message": "keyboard is not installed. Run pip install keyboard"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "No shortcut provided"}

    elif action == "type_text":
        text = payload.get("text")
        if text:
            try:
                import keyboard
                keyboard.write(text, delay=0.01)
                return {"status": "success", "message": f"Typed text"}
            except ImportError:
                return {"status": "error", "message": "keyboard is not installed. Run pip install keyboard"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "No text provided"}

    elif action == "scroll":
        direction = payload.get("direction")
        amount = payload.get("amount", 500)
        if direction:
            try:
                import pyautogui
                pyautogui.FAILSAFE = False
                scroll_amount = amount if direction == "up" else -amount
                pyautogui.scroll(scroll_amount)
                return {"status": "success", "message": f"Scrolled {direction} by {amount}"}
            except ImportError:
                return {"status": "error", "message": "pyautogui is not installed. Run pip install pyautogui"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "No direction provided"}

    elif action == "clipboard_get":
        try:
            import pyperclip
            text = pyperclip.paste()
            return {"status": "success", "text": text}
        except ImportError:
            return {"status": "error", "message": "pyperclip is not installed. Run pip install pyperclip"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    elif action == "clipboard_set":
        text = payload.get("text", "")
        try:
            import pyperclip
            pyperclip.copy(text)
            return {"status": "success", "message": "Clipboard set."}
        except ImportError:
            return {"status": "error", "message": "pyperclip is not installed. Run pip install pyperclip"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    else:
        return {"status": "error", "message": f"Unknown action: {action}"}


# ── Main Loop ────────────────────────────────────────────────────────────────

async def connect_to_brain():
    logger.info(f"Connecting to {RENDER_URL.split('?')[0]}...")
    while True:
        try:
            async with websockets.connect(RENDER_URL) as websocket:
                logger.info("Connected to J.A.R.V.I.S Cloud Brain!")
                
                while True:
                    message_str = await websocket.recv()
                    command = json.loads(message_str)
                    
                    msg_id = command.get("msg_id")
                    logger.info(f"Received command: {command.get('action')}")
                    
                    response_payload = await handle_command(command)
                    response_payload["msg_id"] = msg_id
                    
                    await websocket.send(json.dumps(response_payload))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Connection error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    print("==================================================")
    print("  J.A.R.V.I.S — Local Laptop Client")
    print("==================================================")

    # Start clipboard intelligence monitor if enabled (daemon thread — auto-exits with main)
    if _CLIPBOARD_ENABLED:
        cb_thread = threading.Thread(
            target=_clipboard_monitor_loop,
            daemon=True,
            name="clipboard-monitor",
        )
        cb_thread.start()
    else:
        logger.info(
            "[CLIPBOARD] Intelligence is OFF. "
            "Set CLIPBOARD_INTELLIGENCE_ENABLED=true in .env to enable."
        )

    try:
        asyncio.run(connect_to_brain())
    except KeyboardInterrupt:
        print("\nDisconnected.")

