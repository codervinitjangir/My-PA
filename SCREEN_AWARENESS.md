# Screen Awareness

Built during **Stabilization Sprint 3**.

Screen Awareness allows JARVIS to understand what Boss is currently doing on screen by analyzing a single snapshot.

## Core Rules

1. **Observe Only:** JARVIS never controls the screen, clicks, or types.
2. **Manual Trigger:** The analysis only runs when Boss clicks "👁 Analyze Screen". No continuous monitoring.
3. **No Storage:** Screenshots are deleted from memory immediately after parsing. Nothing is saved to disk.
4. **Frozen Architecture:** No new folders or intelligence abstractions were created.

---

## Architecture

| File | Role |
|---|---|
| `jarvis_os/observers/screen_observer.py` | Captures native screenshot (`PIL`), calls `VisionService`, parses response into `ScreenState`. |
| `app/services/vision_service.py` | **Unmodified**. Groq Llama 4 Scout. |
| `jarvis_os/core/state_manager.py` | Holds the ephemeral `screen` state inside the singleton `_state_mgr`. |
| `app/main.py` | Routes `analyze_screen` and injects state into `/dashboard`. |

---

## The Pipeline

1. **Boss** clicks `👁 Analyze Screen` in dashboard.
2. **Frontend** calls `POST /operator/action {"action": "analyze_screen"}`.
3. **ScreenObserver** captures a single PNG in-memory.
4. **VisionService** reads the image via base64, answers a rigid prompt.
5. Base64 string and raw bytes are `del`'d.
6. **ScreenObserver** extracts Application, Activity, Summary, and Next Action.
7. **ScreenObserver** calculates a **deterministic 0-100 confidence score** (no ML for scoring).
8. State is attached to `GlobalStateManager` and pushed to the dashboard UI.

---

## Cooldown

To prevent API abuse and accidental double-clicks, a strict **15-second cooldown** is enforced on the backend.

If Boss clicks again within 15 seconds, JARVIS refuses the capture.
