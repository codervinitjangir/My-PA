import asyncio
import os
import io
import base64
import json
import logging
import webbrowser
import websockets
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="[LAPTOP] %(message)s")
logger = logging.getLogger()

load_dotenv()

JARVIS_API_TOKEN = os.getenv("JARVIS_API_TOKEN", "").strip()

# Replace with your actual Render URL
RENDER_URL = "wss://jarvis-mcaj.onrender.com/laptop/ws"

if JARVIS_API_TOKEN:
    RENDER_URL += f"?token={JARVIS_API_TOKEN}"

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
        
    elif action == "screenshot":
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
            
    else:
        return {"status": "error", "message": f"Unknown action: {action}"}

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
    try:
        asyncio.run(connect_to_brain())
    except KeyboardInterrupt:
        print("\nDisconnected.")
