"""
Optional: if UptimeRobot is not set up, this self-pings the /health endpoint
every 10 minutes to prevent Render free tier from sleeping.
Started automatically by APScheduler alongside the morning briefing.
"""
import os
import logging
import httpx

logger = logging.getLogger("J.A.R.V.I.S")

RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "")

async def keep_alive_ping():
    if not RENDER_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{RENDER_URL}/health")
            logger.debug("[KEEP-ALIVE] Ping %s → %s", RENDER_URL, r.status_code)
    except Exception as e:
        logger.debug("[KEEP-ALIVE] Ping failed (non-critical): %s", e)
