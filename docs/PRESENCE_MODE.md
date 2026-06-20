# JARVIS Presence Mode

## Overview

JARVIS Presence Mode is the final friction-reduction layer introduced before the v1.0 freeze. It transforms JARVIS from a dashboard-bound web application into a permanent, accessible desktop companion. 

## Architectural Philosophy

- **No Duplicate Intelligence:** It does not think. It does not parse intents. It strictly acts as a remote control for the core backend.
- **Micro-Footprint:** The companion idles at <1% CPU and <100MB RAM. The PySide6 UI loop uses native Qt calls for efficiency.
- **Opt-In Polling:** It fetches data from the backend only when explicitly visible on screen. When hidden to the system tray, all polling halts.

## Features

1. **Always On Top Companion Window:** A 300x220 dark-themed UI that docks in the bottom-right corner. It displays:
   - Greeting / Status indicator.
   - Current Workspace.
   - Current Focus.
   - Pending Task Count.
2. **Native Voice Interface:** The 🎤 Talk button launches a minimal recording dialog that captures microphone audio natively and sends it directly to the existing `/stt` and `/chat` APIs without launching a browser.
3. **One-Click Actions:** Instantly trigger Morning Briefs or Screen Analysis.
4. **System Tray Integration:** A right-click menu provides quick access to the JARVIS dashboard, briefs, and an auto-start toggle.
5. **Windows Startup Integration:** Toggling auto-start dynamically creates a shortcut in your Windows Startup directory, allowing the PySide app to launch silently in the background on boot.

## Setup

The backend must be running at `http://127.0.0.1:8000`.

To start Presence Mode manually:
```bash
pythonw jarvis_desktop/main.py
```
*(Note: `pythonw` ensures no ugly command prompt window is left behind)*
