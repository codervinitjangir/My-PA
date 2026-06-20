# Friction Log

The Friction Log is a simple productivity utility built during **Stabilization Sprint 1**.

It is NOT an intelligence system. It is a note-taking tool that lives inside the JARVIS dashboard.

---

## Purpose

Boss can log friction points as they occur:

```
"Dashboard loads slowly"
"Morning brief is too long"
"Need GitHub shortcut"
```

And later mark them fixed (or delete them).

This creates a direct feedback loop: friction noticed → friction logged → friction resolved → better JARVIS.

---

## Architecture

Everything lives in **existing** allowed locations. No new folders.

| File | Role |
|---|---|
| `jarvis_os/core/friction.py` | 5 pure functions. No classes. |
| `jarvis_os/core/friction_log.json` | Single flat JSON file. |
| `app/main.py` | 4 endpoints (GET, POST, PATCH, DELETE). |
| `frontend/components/dashboard.js` | Friction section rendered below dashboard. |
| `frontend/style.css` | Friction UI styles. |

---

## API

| Endpoint | Method | Description |
|---|---|---|
| `/frictions` | GET | Get all items (open first) |
| `/frictions` | POST | Add new: `{"text": "..."}` |
| `/frictions/{id}` | PATCH | Mark resolved |
| `/frictions/{id}` | DELETE | Delete permanently |

---

## Performance

All operations execute in < 5ms (file I/O on local disk). Zero LLM. Zero network.

---

## Rules

- No database.
- No AI.
- No embeddings.
- No background workers.
- One JSON file. That's it.
