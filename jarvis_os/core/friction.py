import json
import uuid
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

_FRICTION_FILE = Path(__file__).parent / "friction_log.json"


def _load() -> List[Dict[str, Any]]:
    if not _FRICTION_FILE.exists():
        _FRICTION_FILE.write_text("[]", encoding="utf-8")
        return []
    try:
        return json.loads(_FRICTION_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(data: List[Dict[str, Any]]) -> None:
    _FRICTION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def add_friction(text: str) -> Dict[str, Any]:
    """Add a new open friction item. Returns the created item."""
    item = {
        "id": str(uuid.uuid4()),
        "text": text.strip(),
        "status": "open",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "resolved_at": None,
    }
    data = _load()
    data.append(item)
    _save(data)
    return item


def get_frictions() -> List[Dict[str, Any]]:
    """Return all friction items, open first then resolved."""
    data = _load()
    return sorted(data, key=lambda x: (x["status"] != "open", x["created_at"]))


def resolve_friction(friction_id: str) -> Optional[Dict[str, Any]]:
    """Mark a friction item as resolved. Returns the updated item or None."""
    data = _load()
    for item in data:
        if item["id"] == friction_id:
            item["status"] = "resolved"
            item["resolved_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            _save(data)
            return item
    return None


def delete_friction(friction_id: str) -> bool:
    """Permanently delete a friction item. Returns True if deleted."""
    data = _load()
    original_len = len(data)
    data = [item for item in data if item["id"] != friction_id]
    if len(data) < original_len:
        _save(data)
        return True
    return False


def get_open_count() -> int:
    """Return the count of open (unresolved) friction items."""
    return sum(1 for item in _load() if item["status"] == "open")
