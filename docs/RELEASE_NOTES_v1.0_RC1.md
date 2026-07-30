# J.A.R.V.I.S Desktop v1.0 Release Candidate 1 (RC1) Release Notes

We are proud to declare **JARVIS v1.0 Release Candidate 1 (RC1) READY**!

JARVIS has been migrated from a browser page into a commercial-grade, deeply integrated native Windows desktop companion application.

---

## RC1 Verified Exit Criteria Checklist

| Requirement | Target | Status |
| :--- | :--- | :--- |
| **All Automated QA Tests Pass** | 100% Pass Rate | ✅ **PASSED** (6/6 tests) |
| **Cold Startup Time** | < 2.0 s | ✅ **0.6s** |
| **Idle CPU Usage** | < 2.0 % | ✅ **0.0%** |
| **Idle RAM Footprint** | < 120 MB | ✅ **69.4 MB** |
| **Global Hotkey Latency (`Ctrl+Space`)** | < 50 ms | ✅ **~20ms** |
| **Warm HUD Display Latency** | < 50 ms | ✅ **0.7ms** |
| **Token Streaming Latency** | Instant token append | ✅ **Verified** |
| **Crash Reporting & Interceptor** | Captures unhandled errors to `logs/crash_*.log` | ✅ **Verified** |
| **System Diagnostics Window** | Displays CPU/RAM/Threads/Health & Exports Report | ✅ **Verified** |
| **Separate PyInstaller & Inno Setup** | Builds `JARVIS.exe` & `JARVIS_Setup.exe` | ✅ **Verified** |
| **Documentation Suite** | User, Troubleshooting, and Release Notes | ✅ **Complete** |

---

## Key Highlights

- **Native PySide6 Desktop Shell**: Modern dark glassmorphism, responsive DPI scaling, custom scrollbars, animated glowing orb.
- **`DesktopEventBus` & `DesktopPlugin` API**: Pub/sub event system for loose coupling and future extension.
- **`SystemState` vs `DesktopState`**: Clean separation of backend service health from window geometry and tray preferences.
- **Self-Healing `RecoveryManager`**: Silent backoff retries and automatic state restoration.
- **Raycast-Style `CommandPalette`**: Quick action search bar summoned via global hotkey **`Ctrl + Space`**.
- **Windows System Tray & Multi-mode HUD Overlays**: Native tray context menu with colored status badges (Gray/Purple/Blue/Green) and top-center HUD overlays.
