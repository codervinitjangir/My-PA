"""
jarvis_desktop/laptop_client.py

Lightweight WebSocket Companion Client.
Connects your local laptop to the JARVIS backend running on Render (cloud).

Handles two server commands:
  - open_app       : Opens a local application / URL using os.startfile
  - capture_screen : Takes a screenshot and returns it as base64 to the server

Usage:
    python -m jarvis_desktop.laptop_client
    OR via start_client.bat
"""

import asyncio
import base64
import io
import json
import logging
import os
import sys
import subprocess

try:
    import websockets
except ImportError:
    print("[ERROR] websockets library not found. Run: pip install websockets")
    sys.exit(1)

from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
RENDER_URL = os.getenv("RENDER_URL", "").rstrip("/")
API_TOKEN  = os.getenv("JARVIS_API_TOKEN", "")

if not RENDER_URL:
    print("[ERROR] RENDER_URL is not set in your .env file.")
    print("  Add: RENDER_URL=https://your-app.onrender.com")
    sys.exit(1)

# Build WebSocket URL (wss:// for https://, ws:// for http://)
WS_URL = RENDER_URL.replace("https://", "wss://").replace("http://", "ws://") + "/laptop/ws"
if API_TOKEN:
    WS_URL += f"?token={API_TOKEN}"

RECONNECT_DELAY_INITIAL = 5   # seconds before first retry
RECONNECT_DELAY_MAX     = 60  # cap backoff at 60 seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("JARVIS.LaptopClient")


# ── Handlers ──────────────────────────────────────────────────────────────────

def handle_open_app(payload: dict) -> dict:
    """Open a local application or URL."""
    target = (payload.get("target") or "").strip()
    if not target:
        return {"status": "error", "message": "No target specified"}

    try:
        os.startfile(target)
        logger.info("[OPEN] Opened: %s", target)
        return {"status": "success", "message": f"Opened {target}"}
    except Exception as e:
        # Fallback: try via shell start command
        try:
            subprocess.Popen(["start", "", target], shell=True)
            logger.info("[OPEN] Opened via shell: %s", target)
            return {"status": "success", "message": f"Opened {target}"}
        except Exception as e2:
            logger.error("[OPEN] Failed to open %s: %s", target, e2)
            return {"status": "error", "message": str(e2)}


def handle_capture_screen(payload: dict) -> dict:
    """Take a screenshot and return as base64."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        raw_bytes = buf.getvalue()
        buf.close()
        img.close()
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        logger.info("[SCREEN] Screenshot captured (%d bytes)", len(raw_bytes))
        return {"status": "success", "image_b64": b64}
    except ImportError:
        return {"status": "error", "message": "Pillow not installed. Run: pip install Pillow"}
    except Exception as e:
        logger.error("[SCREEN] Capture failed: %s", e)
        return {"status": "error", "message": str(e)}


# ── Dispatch ──────────────────────────────────────────────────────────────────

HANDLERS = {
    "open_app":       handle_open_app,
    "capture_screen": handle_capture_screen,
}


async def _process(websocket, message: str):
    """Parse and dispatch a server command, then send the response back."""
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        logger.warning("[WS] Received non-JSON message: %s", message[:100])
        return

    action  = data.get("action", "")
    msg_id  = data.get("msg_id", "")
    payload = data.get("payload", {})

    handler = HANDLERS.get(action)
    if handler:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, handler, payload)
    else:
        logger.warning("[WS] Unknown action: %s", action)
        result = {"status": "error", "message": f"Unknown action: {action}"}

    result["msg_id"] = msg_id
    await websocket.send(json.dumps(result))


# ── Main Loop ─────────────────────────────────────────────────────────────────

async def connect_and_listen():
    """Connect to Render, listen for commands, reconnect on failure."""
    delay = RECONNECT_DELAY_INITIAL
    while True:
        try:
            logger.info("[WS] Connecting to %s ...", WS_URL)
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=30) as ws:
                logger.info("[WS] Connected to JARVIS server! Waiting for commands...")
                delay = RECONNECT_DELAY_INITIAL  # reset backoff on success
                async for message in ws:
                    asyncio.ensure_future(_process(ws, message))

        except websockets.exceptions.ConnectionClosedOK:
            logger.info("[WS] Server closed the connection gracefully.")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("[WS] Connection closed with error: %s", e)
        except OSError as e:
            logger.warning("[WS] Network error: %s", e)
        except Exception as e:
            logger.error("[WS] Unexpected error: %s", e)

        logger.info("[WS] Reconnecting in %ds...", delay)
        await asyncio.sleep(delay)
        delay = min(delay * 2, RECONNECT_DELAY_MAX)


def main():
    print("=" * 55)
    print("  J.A.R.V.I.S  Laptop Companion Client")
    print("=" * 55)
    print(f"  Server : {RENDER_URL}")
    print(f"  Token  : {'set' if API_TOKEN else 'not set (open endpoint)'}")
    print("=" * 55)
    print("  Press Ctrl+C to stop.\n")
    try:
        asyncio.run(connect_and_listen())
    except KeyboardInterrupt:
        print("\n[INFO] Laptop client stopped.")


if __name__ == "__main__":
    main()
