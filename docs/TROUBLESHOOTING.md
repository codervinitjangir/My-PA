# J.A.R.V.I.S Desktop Troubleshooting & Self-Healing Guide

JARVIS includes built-in self-healing recovery and diagnostic logging.

---

## 1. Automatic Error Recovery

If the local FastAPI server disconnects or your network drops:
1. **RecoveryManager** automatically detects connection loss.
2. Displays notification: `Lost connection... Attempting silent reconnect`.
3. Performs exponential backoff retries (2s, 4s, 6s, 8s, 10s).
4. Restores connection automatically without restarting the application: `Connection restored successfully`.

---

## 2. Diagnostics Window & Exporting Reports

To check live system metrics and service health:
1. Click **`⚙️ Settings`** or press `Ctrl + Space` and select `System Diagnostics`.
2. View real-time CPU %, RAM MB, Active Threads, and Service Health (Backend, Voice, Telegram, Memory DB, Internet).
3. Click **`📥 Export Report`** to generate a diagnostic text dump file (`jarvis_diagnostics.txt`).

---

## 3. Log Locations & Crash Dumps

- **Main Application Log**: `logs/jarvis_desktop.log`
- **Crash Dumps**: `logs/crash_<timestamp>.log` (generated automatically if an unhandled Python exception occurs).

To view logs directly:
```cmd
type logs\jarvis_desktop.log
```
