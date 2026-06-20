import json
import time
from pathlib import Path
from typing import Dict, Any

_USAGE_FILE = Path(__file__).parent / "usage_log.json"

_DEFAULT: Dict[str, Any] = {
    "dashboard_open": 0,
    "morning_brief": 0,
    "screen_analysis": 0,
    "session_resume": 0,
    "browser_open": 0,
    "quick_links": {},
    "daily_history": {},
}


def _load() -> Dict[str, Any]:
    if not _USAGE_FILE.exists():
        _USAGE_FILE.write_text(json.dumps(_DEFAULT, indent=2), encoding="utf-8")
        return dict(_DEFAULT)
    try:
        data = json.loads(_USAGE_FILE.read_text(encoding="utf-8"))
        # Back-fill missing keys
        for k, v in _DEFAULT.items():
            if k not in data:
                data[k] = v
        return data
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT)


def _save(data: Dict[str, Any]) -> None:
    _USAGE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def track_event(event_name: str) -> None:
    """Increment a named event counter (global + today's date bucket)."""
    data = _load()
    data[event_name] = data.get(event_name, 0) + 1

    today = _today()
    if today not in data["daily_history"]:
        data["daily_history"][today] = {}
    day = data["daily_history"][today]
    day[event_name] = day.get(event_name, 0) + 1

    _save(data)


def track_site(site_name: str) -> None:
    """Increment a quick-link site counter."""
    data = _load()
    data["quick_links"][site_name] = data["quick_links"].get(site_name, 0) + 1

    today = _today()
    if today not in data["daily_history"]:
        data["daily_history"][today] = {}
    day = data["daily_history"][today]
    key = f"site:{site_name}"
    day[key] = day.get(key, 0) + 1

    _save(data)


def get_usage_summary() -> Dict[str, Any]:
    """Return all-time usage data."""
    return _load()


def get_today_summary() -> Dict[str, Any]:
    """Return today's usage data + usage score."""
    data = _load()
    today = _today()
    today_data = data.get("daily_history", {}).get(today, {})

    total = sum(v for k, v in today_data.items() if not k.startswith("site:"))
    sites_today = {k[5:]: v for k, v in today_data.items() if k.startswith("site:")}

    if total > 10:
        score = "high"
        score_label = "🟢 High"
    elif total >= 5:
        score = "medium"
        score_label = "🟡 Medium"
    else:
        score = "low"
        score_label = "🔴 Low"

    # Most and least used feature (non-site events)
    feature_counts = {k: v for k, v in today_data.items() if not k.startswith("site:")}
    most_used = max(feature_counts, key=feature_counts.get) if feature_counts else None
    least_used = min(feature_counts, key=feature_counts.get) if feature_counts else None

    return {
        "date": today,
        "events": today_data,
        "features": feature_counts,
        "sites": sites_today,
        "total": total,
        "score": score,
        "score_label": score_label,
        "most_used": most_used,
        "least_used": least_used,
    }


def reset_today() -> None:
    """Clear today's usage bucket (for testing)."""
    data = _load()
    today = _today()
    data.get("daily_history", {}).pop(today, None)
    _save(data)
