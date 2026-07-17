"""
jarvis_desktop/laptop_client.py

Lightweight WebSocket Companion Client.
Connects your local laptop to the JARVIS backend running on Render (cloud).

Handles two server commands:
  - open_app       : Opens a local application / URL using os.startfile
  - capture_screen : Takes a screenshot and returns it as base64 to the server

With Always-On Wake Word functionality built-in.
"""

import asyncio
import base64
import io
import json
import logging
import os
import sys
import subprocess
import threading
import queue
import tempfile
import time
import wave
import uuid
import requests
import numpy as np

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
API_KEY    = os.getenv("JARVIS_API_KEY", "")
WAKE_WORD_ENABLED = os.getenv("JARVIS_WAKE_WORD_ENABLED", "true").lower() == "true"

if not RENDER_URL:
    print("[ERROR] RENDER_URL is not set in your .env file.")
    print("  Add: RENDER_URL=https://your-app.onrender.com")
    sys.exit(1)

# Build WebSocket URL
WS_URL = RENDER_URL.replace("https://", "wss://").replace("http://", "ws://") + "/laptop/ws"
if API_TOKEN:
    WS_URL += f"?token={API_TOKEN}"

# Build Auth Headers for HTTP Requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
if API_TOKEN:
    HEADERS["Authorization"] = f"Bearer {API_TOKEN}"
if API_KEY:
    HEADERS["X-API-Key"] = API_KEY

RECONNECT_DELAY_INITIAL = 5
RECONNECT_DELAY_MAX     = 60

# Backend chat API requires a strict UUID4 session ID
CLIENT_SESSION_ID = str(uuid.uuid4())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("JARVIS.LaptopClient")


# ── Handlers ──────────────────────────────────────────────────────────────────

def handle_open_app(payload: dict) -> dict:
    target = (payload.get("target") or "").strip()
    if not target:
        return {"status": "error", "message": "No target specified"}
    try:
        os.startfile(target)
        logger.info("[OPEN] Opened: %s", target)
        return {"status": "success", "message": f"Opened {target}"}
    except Exception as e:
        try:
            subprocess.Popen(["start", "", target], shell=True)
            logger.info("[OPEN] Opened via shell: %s", target)
            return {"status": "success", "message": f"Opened {target}"}
        except Exception as e2:
            logger.error("[OPEN] Failed to open %s: %s", target, e2)
            return {"status": "error", "message": str(e2)}

def handle_capture_screen(payload: dict) -> dict:
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
        return {"status": "error", "message": "Pillow not installed."}
    except Exception as e:
        logger.error("[SCREEN] Capture failed: %s", e)
        return {"status": "error", "message": str(e)}

def handle_keyboard_shortcut(payload: dict) -> dict:
    try:
        import keyboard
        shortcut = payload.get("shortcut", "")
        if shortcut:
            keyboard.send(shortcut)
            logger.info("[ACTION] Keyboard shortcut: %s", shortcut)
            return {"status": "success"}
        return {"status": "error", "message": "No shortcut provided"}
    except ImportError:
        return {"status": "error", "message": "keyboard package not installed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def handle_type_text(payload: dict) -> dict:
    try:
        import keyboard
        text = payload.get("text", "")
        if text:
            keyboard.write(text)
            logger.info("[ACTION] Typed text: %s", text)
            return {"status": "success"}
        return {"status": "error", "message": "No text provided"}
    except ImportError:
        return {"status": "error", "message": "keyboard package not installed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def handle_scroll(payload: dict) -> dict:
    try:
        import pyautogui
        direction = payload.get("direction", "down")
        amount = payload.get("amount", 300)
        scroll_val = amount if direction == "up" else -amount
        pyautogui.scroll(scroll_val)
        logger.info("[ACTION] Scrolled %s by %s", direction, amount)
        return {"status": "success"}
    except ImportError:
        return {"status": "error", "message": "pyautogui package not installed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

HANDLERS = {
    "open_app":          handle_open_app,
    "capture_screen":    handle_capture_screen,
    "keyboard_shortcut": handle_keyboard_shortcut,
    "type_text":         handle_type_text,
    "scroll":            handle_scroll,
}

async def _process(websocket, message: str):
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return
    action  = data.get("action", "")
    msg_id  = data.get("msg_id", "")
    payload = data.get("payload", {})
    handler = HANDLERS.get(action)
    if handler:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, handler, payload)
    else:
        result = {"status": "error", "message": f"Unknown action: {action}"}
    result["msg_id"] = msg_id
    await websocket.send(json.dumps(result))

async def connect_and_listen():
    delay = RECONNECT_DELAY_INITIAL
    while True:
        try:
            logger.info("[WS] Connecting to %s ...", WS_URL)
            async with websockets.connect(
                WS_URL, 
                ping_interval=20, 
                ping_timeout=30,
                user_agent_header=HEADERS["User-Agent"]
            ) as ws:
                logger.info("[WS] Connected to JARVIS server!")
                delay = RECONNECT_DELAY_INITIAL
                async for message in ws:
                    asyncio.ensure_future(_process(ws, message))
        except websockets.exceptions.ConnectionClosedOK:
            pass
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("[WS] Closed with error: %s", e)
        except OSError as e:
            logger.warning("[WS] Network error: %s", e)
        except Exception as e:
            logger.error("[WS] Unexpected error: %s", e)
        await asyncio.sleep(delay)
        delay = min(delay * 2, RECONNECT_DELAY_MAX)

# ── Wake Word Daemon ──────────────────────────────────────────────────────────

WAKE_WORD_PAUSED = False
QUIT_FLAG = False
TRAY_ICON = None

def generate_tray_icon(listening=True):
    try:
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (64, 64), color=(0, 0, 0))
        d = ImageDraw.Draw(image)
        color = (0, 255, 0) if listening else (255, 0, 0)
        d.ellipse((16, 16, 48, 48), fill=color)
        return image
    except ImportError:
        return None

def on_pause_resume(icon, item):
    global WAKE_WORD_PAUSED, TRAY_ICON
    WAKE_WORD_PAUSED = not WAKE_WORD_PAUSED
    if TRAY_ICON:
        TRAY_ICON.icon = generate_tray_icon(not WAKE_WORD_PAUSED)
        TRAY_ICON.title = "JARVIS: Listening" if not WAKE_WORD_PAUSED else "JARVIS: Paused"

def on_quit(icon, item):
    global QUIT_FLAG, TRAY_ICON
    QUIT_FLAG = True
    if TRAY_ICON:
        TRAY_ICON.stop()
    os._exit(0)

def run_tray_icon():
    global TRAY_ICON
    try:
        from pystray import Icon, Menu, MenuItem
        img = generate_tray_icon(not WAKE_WORD_PAUSED)
        if not img:
            return
        TRAY_ICON = Icon("JARVIS", img, "JARVIS: Listening")
        TRAY_ICON.menu = Menu(
            MenuItem(lambda text: "Resume" if WAKE_WORD_PAUSED else "Pause", on_pause_resume),
            MenuItem("Quit", on_quit)
        )
        TRAY_ICON.run()
    except Exception as e:
        logger.error("[TRAY] Failed to start system tray icon: %s", e)

def beep():
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        pass

def wake_word_thread():
    global WAKE_WORD_PAUSED, QUIT_FLAG
    try:
        import sounddevice as sd
        from openwakeword.model import Model
    except ImportError as e:
        logger.error("[WAKE] Missing dependency: %s", e)
        return

    logger.info("[WAKE] Loading openwakeword model 'hey_jarvis'...")
    try:
        owwModel = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
    except Exception as e:
        logger.error("[WAKE] Failed to load openwakeword: %s", e)
        return
        
    logger.info("[WAKE] Model loaded. Monitoring microphone...")

    FORMAT = np.int16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1280

    audio_queue = queue.Queue()

    def callback(indata, frames, time, status):
        if status:
            pass # ignore warnings
        audio_queue.put(indata.copy())

    # Wait a moment for UI/models
    time.sleep(1)

    while not QUIT_FLAG:
        if WAKE_WORD_PAUSED:
            time.sleep(0.5)
            continue
            
        try:
            # We explicitly open the stream. If Paused, we exit this inner loop and close the stream.
            with sd.InputStream(samplerate=RATE, channels=CHANNELS, dtype=FORMAT, blocksize=CHUNK, callback=callback):
                logger.info("[WAKE] Input stream started.")
                
                # clear queue
                while not audio_queue.empty():
                    audio_queue.get()

                while not QUIT_FLAG and not WAKE_WORD_PAUSED:
                    try:
                        audio_chunk = audio_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue
                        
                    pcm = audio_chunk.flatten()
                    prediction = owwModel.predict(pcm)
                    
                    for mdl, score in prediction.items():
                        if score > 0.1:
                            logger.info("[WAKE] Partial match score: %.2f", score)
                            
                        if score > 0.4:
                            logger.info("[WAKE] Wake word detected! (Score: %.2f)", score)
                            handle_wake_detection()
                            
                            # Flush queue so we don't immediately double trigger
                            while not audio_queue.empty():
                                audio_queue.get()
                            break
                            
            logger.info("[WAKE] Input stream stopped (Paused).")
            
        except Exception as e:
            logger.error("[WAKE] InputStream error: %s", e)
            time.sleep(2)

def handle_wake_detection():
    beep()
    
    import sounddevice as sd
    RATE = 16000
    CHANNELS = 1
    FORMAT = np.int16
    MAX_SECS = 5
    SILENCE_SECS = 1.5
    SILENCE_THRESHOLD = 500

    frames = []
    silent_chunks = 0
    chunks_per_sec = RATE / 1024
    max_silent_chunks = int(SILENCE_SECS * chunks_per_sec)

    logger.info("[WAKE] Recording...")
    
    with sd.InputStream(samplerate=RATE, channels=CHANNELS, dtype=FORMAT, blocksize=1024) as stream:
        for _ in range(int(MAX_SECS * chunks_per_sec)):
            data, overflow = stream.read(1024)
            frames.append(data)
            rms = np.sqrt(np.mean(data.astype(np.float32)**2))
            
            if rms < SILENCE_THRESHOLD:
                silent_chunks += 1
            else:
                silent_chunks = 0
                
            if silent_chunks > max_silent_chunks:
                logger.info("[WAKE] Silence detected, stopping.")
                break

    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    
    wav_bytes = wav_io.getvalue()
    wav_io.close()

    # STT Request
    stt_url = f"{RENDER_URL}/stt"
    try:
        files = {'file': ('audio.wav', wav_bytes, 'audio/wav')}
        r = requests.post(stt_url, headers=HEADERS, files=files, timeout=10)
        r.raise_for_status()
        stt_resp = r.json()
        text = stt_resp.get("text", "").strip()
        if not text:
            logger.info("[WAKE] No speech detected.")
            return
        logger.info("[WAKE] Recognized: %s", text)
    except Exception as e:
        logger.error("[WAKE] STT failed: %s", e)
        return
        
    # Chat Request
    chat_url = f"{RENDER_URL}/chat"
    try:
        chat_req = {"message": text, "session_id": CLIENT_SESSION_ID}
        h = HEADERS.copy()
        h["Content-Type"] = "application/json"
        
        r2 = requests.post(chat_url, headers=h, json=chat_req, timeout=30)
        r2.raise_for_status()
        chat_resp = r2.json()
        reply_text = chat_resp.get("response", "").strip()
        logger.info("[WAKE] JARVIS replied: %s", reply_text)
        
        # --- Auto-Open URLs ---
        # If JARVIS included a URL in his reply (e.g. for "open youtube"), open it!
        import re
        urls = re.findall(r'(https?://[^\s)\]]+)', reply_text)
        if urls:
            try:
                os.startfile(urls[0])
                logger.info("[WAKE] Auto-opened URL from reply: %s", urls[0])
            except Exception as e:
                logger.error("[WAKE] Failed to auto-open URL: %s", e)
        
        if reply_text:
            # Strip the URL so Jarvis doesn't awkwardly read out "h t t p s colon slash slash..."
            speak_text = re.sub(r'https?://[^\s)\]]+', '', reply_text).strip()
            if not speak_text and urls:
                speak_text = "Opening that for you, sir."
            if speak_text:
                play_tts(speak_text)
            
    except Exception as e:
        logger.error("[WAKE] Chat failed: %s", e)

def play_tts(text):
    tts_url = f"{RENDER_URL}/tts"
    try:
        import pygame
        h = HEADERS.copy()
        h["Content-Type"] = "application/json"
        
        r = requests.post(tts_url, headers=h, json={"text": text}, stream=True, timeout=20)
        r.raise_for_status()
        
        fd, temp_path = tempfile.mkstemp(suffix=".mp3")
        with os.fdopen(fd, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    
        logger.info("[WAKE] Playing TTS response...")
        from playsound import playsound
        playsound(temp_path)
        
        try:
            os.remove(temp_path)
        except Exception:
            pass
        
    except Exception as e:
        logger.error("[WAKE] TTS play failed: %s", e)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  J.A.R.V.I.S  Laptop Companion Client")
    print("=" * 55)
    print(f"  Server    : {RENDER_URL}")
    print(f"  Token     : {'set' if API_TOKEN else 'not set'}")
    print(f"  API Key   : {'set' if API_KEY else 'not set'}")
    print(f"  Wake Word : {'Enabled' if WAKE_WORD_ENABLED else 'Disabled'}")
    print("=" * 55)
    print("  Press Ctrl+C to stop.\n")

    if WAKE_WORD_ENABLED:
        threading.Thread(target=wake_word_thread, daemon=True).start()
        threading.Thread(target=run_tray_icon, daemon=True).start()

    try:
        asyncio.run(connect_and_listen())
    except KeyboardInterrupt:
        print("\n[INFO] Laptop client stopped.")
        global QUIT_FLAG
        QUIT_FLAG = True
        os._exit(0)

if __name__ == "__main__":
    main()

