"""
app/core/reliability/circuit_breaker.py — Async Circuit Breaker Pattern for External APIs

Prevents cascading system failures during third-party API outages (Groq, Gemini, Tavily, ElevenLabs).
States: CLOSED (normal), OPEN (fast-failing to fallback), HALF_OPEN (testing recovery).
"""

import time
import asyncio
import logging
from typing import Callable, Any, Optional

logger = logging.getLogger("J.A.R.V.I.S.CircuitBreaker")

class CircuitBreakerOpenException(Exception):
    """Raised when an API call is attempted while circuit breaker is OPEN."""
    pass

class AsyncCircuitBreaker:
    """
    Lightweight async circuit breaker for external network services.
    """
    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout_sec: float = 30.0
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count = 0
        self.last_state_change = time.time()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function wrapped by circuit breaker protection."""
        now = time.time()

        if self.state == "OPEN":
            if now - self.last_state_change > self.recovery_timeout_sec:
                logger.info("[CIRCUIT-BREAKER] '%s' transitioning from OPEN to HALF_OPEN", self.name)
                self.state = "HALF_OPEN"
                self.last_state_change = now
            else:
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' is OPEN. Fast-failing external call."
                )

        try:
            result = await func(*args, **kwargs)
            
            if self.state == "HALF_OPEN":
                logger.info("[CIRCUIT-BREAKER] '%s' recovered successfully, transitioning to CLOSED", self.name)
                self.state = "CLOSED"
                self.failure_count = 0
                self.last_state_change = now
            elif self.state == "CLOSED":
                self.failure_count = 0
                
            return result

        except Exception as e:
            self.failure_count += 1
            logger.warning("[CIRCUIT-BREAKER] '%s' call failed (%d/%d): %s", 
                           self.name, self.failure_count, self.failure_threshold, e)

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.last_state_change = now
                logger.error("[CIRCUIT-BREAKER] '%s' threshold breached! Circuit is now OPEN.", self.name)
                
            raise e
