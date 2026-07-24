"""
app/routes/system_routes.py — Modular FastAPI System Router

Endpoints for health check, system usage, executive briefing, and latency telemetry.
"""

from fastapi import APIRouter, HTTPException
from app.core.voice.latency_tracker import LatencyTracker
from app.core.config import settings

router = APIRouter(tags=["System & Telemetry"])

@router.get("/health")
async def health_check():

    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }

@router.get("/usage")
async def get_usage():
    """Returns today's usage summary and all-time totals."""
    try:
        from jarvis_os.core.usage import get_today_summary
        return get_today_summary()
    except Exception as e:
        return {"today": {}, "totals": {}, "error": str(e)}

@router.get("/api/latency/dashboard")
async def get_latency_dashboard():
    """Returns live voice interaction latency percentiles (P50/P95/P99) and recent turn metrics."""
    tracker = LatencyTracker()
    percentiles = tracker.get_percentiles()
    recent = [r.model_dump() for r in tracker.records[-20:]]
    regressions = [r.model_dump() for r in tracker.records[-20:] if r.is_regression]
    return {
        "status": "healthy" if not regressions else "regression_warning",
        "total_recorded_turns": len(tracker.records),
        "percentiles": percentiles,
        "active_regressions_count": len(regressions),
        "recent_regressions": regressions,
        "recent_interactions": recent
    }
