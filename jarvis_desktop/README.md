# JARVIS Presence Mode

A minimal, friction-reduction desktop companion for JARVIS using PySide6.

## Features
- **Always Accessible:** Resides in your system tray and bottom-right corner.
- **Zero Duplication:** Reuses existing FastAPI endpoints from the core JARVIS backend.
- **Voice Native:** Speak directly into the companion to invoke JARVIS tasks via `/stt` and `/chat`.
- **Minimal Footprint:** Refresh loops stop when hidden, and resource usage is kept tiny.

## Running
```bash
python jarvis_desktop/main.py
```

## Configuration
It automatically connects to `http://127.0.0.1:8000`. No additional configuration is required.
