# JARVIS Desktop Audit: Voice Pipeline Report (VOICE_AUDIT.md)

## 1. Executive Summary
This report audits the complete voice interaction pipeline, state transitions, barge-in support, and status feedback across HUD, Tray, and Main Window.

---

## 2. Voice Pipeline State Machine

```
Sleeping ──► Wake Word ──► Listening ──► Recording ──► Uploading
                                                         │
                                                         ▼
Completed ◄── Speaking ◄── Streaming ◄── Thinking ◄── STT / Routing
```

### Granular Voice States Tracked in `SystemState`:
1. `Sleeping`: Low-power background listening.
2. `Wake Word`: "Hey Jarvis" keyword match triggered.
3. `Listening`: Microphone active.
4. `Recording`: Capturing user speech buffer.
5. `Uploading`: Sending audio bytes to backend STT.
6. `Routing`: LLM intent routing.
7. `Thinking`: Response generation.
8. `Streaming`: Token streaming in progress.
9. `Speaking`: TTS audio playback.
10. `Interrupted`: User barge-in triggered during TTS output.
11. `Completed`: Task finished.
12. `Idle`: Ready for next command.

---

## 3. UI Synchronization & Barge-In Support

- **Tray Badge Feedback**: Automatically updates tray icon badge (Blue=Listening, Green=Speaking/Executing, Purple=Idle).
- **Overlay HUD Sync**: `OverlayManager` displays `🎤 Listening...` -> `🧠 Thinking...` -> `🔊 Speaking...` -> `✓ Done`.
- **Speech Interruption (Barge-in)**: Supported via `toggle_voice_interrupt` setting, allowing user voice input to stop active TTS playback immediately.
