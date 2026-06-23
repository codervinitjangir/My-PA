import threading
from typing import Callable, List, Any
import logging

logger = logging.getLogger("J.A.R.V.I.S")

class EventBus:
    """
    Thread-safe Publisher/Subscriber event bus.
    """
    def __init__(self, name: str):
        self.name = name
        self._subscribers: List[Callable[[Any], None]] = []
        self._lock = threading.Lock()

    def subscribe(self, callback: Callable[[Any], None]):
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Any], None]):
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def publish(self, event: Any):
        with self._lock:
            subs = list(self._subscribers)
            
        for sub in subs:
            try:
                sub(event)
            except Exception as e:
                logger.error(f"[{self.name}] Subscriber error: {e}")
