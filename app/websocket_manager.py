import asyncio
import uuid
import time
import logging
from typing import Optional
from fastapi import WebSocket

logger = logging.getLogger("J.A.R.V.I.S.WebSocket")

class LaptopConnectionManager:
    def __init__(self):
        self.active_connection: Optional[WebSocket] = None
        self.responses = {}
        self.loop = None

    def connect(self, websocket: WebSocket):
        self.active_connection = websocket
        self.loop = asyncio.get_running_loop()
        logger.info("[WEBSOCKET] Laptop client connected.")

    def disconnect(self):
        self.active_connection = None
        logger.info("[WEBSOCKET] Laptop client disconnected.")

    def is_connected(self) -> bool:
        return self.active_connection is not None

    async def handle_incoming(self, data: dict):
        """Handle incoming messages from the laptop."""
        msg_id = data.get("msg_id")
        if msg_id:
            self.responses[msg_id] = data
            logger.debug(f"[WEBSOCKET] Received response for {msg_id}")

    def send_and_wait(self, action: str, payload: dict = None, timeout: int = 15) -> dict:
        """
        Synchronously send a command to the laptop and wait for the response.
        Useful for calling from synchronous tools (ThreadPoolExecutor).
        """
        if not self.is_connected():
            return {"status": "error", "message": "Laptop is offline"}

        msg_id = str(uuid.uuid4())
        message = {
            "msg_id": msg_id,
            "action": action,
            "payload": payload or {}
        }

        # Send message asynchronously
        async def _send():
            try:
                await self.active_connection.send_json(message)
            except Exception as e:
                logger.error(f"[WEBSOCKET] Send error: {e}")
                self.disconnect()

        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(_send(), self.loop)
        else:
            return {"status": "error", "message": "Event loop not running"}

        # Wait synchronously for response
        start_time = time.time()
        while time.time() - start_time < timeout:
            if msg_id in self.responses:
                return self.responses.pop(msg_id)
            time.sleep(0.1)

        return {"status": "error", "message": "Timeout waiting for laptop response"}

    async def send_and_wait_async(self, action: str, payload: dict = None, timeout: int = 15) -> dict:
        """Asynchronous version of send_and_wait"""
        if not self.is_connected():
            return {"status": "error", "message": "Laptop is offline"}

        msg_id = str(uuid.uuid4())
        message = {
            "msg_id": msg_id,
            "action": action,
            "payload": payload or {}
        }

        try:
            await self.active_connection.send_json(message)
        except Exception as e:
            logger.error(f"[WEBSOCKET] Send error: {e}")
            self.disconnect()
            return {"status": "error", "message": "Disconnected during send"}

        start_time = time.time()
        while time.time() - start_time < timeout:
            if msg_id in self.responses:
                return self.responses.pop(msg_id)
            await asyncio.sleep(0.1)

        return {"status": "error", "message": "Timeout waiting for laptop response"}

# Singleton instance
laptop_manager = LaptopConnectionManager()
