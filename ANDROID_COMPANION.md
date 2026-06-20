# Android Companion Architecture

This document outlines the architecture, flow, and setup instructions for the **Android Companion** built during Phase 4 Part 1.

## Architecture Rules

According to the JARVIS MANIFESTO:
1. **Android never owns business logic.**
2. **Android never creates intelligence.**
3. **Android never stores memory.**
4. **Android only consumes existing endpoints.**
5. **If Android can be deleted without affecting JARVIS, the architecture is correct.**

The Android Companion is strictly a remote control interface. It holds no state other than the PC's IP address.

## API Flow Diagram

```text
Boss (Android Device)
  │
  ├─ [1] Opens App (Home Tab)
  │   └── GET http://<PC_IP>:8000/health (latency check)
  │   └── GET http://<PC_IP>:8000/mobile/state (fetches simple JSON)
  │
  ├─ [2] Clicks "Trigger Morning Brief"
  │   └── POST http://<PC_IP>:8000/operator/action { "action": "morning_brief" }
  │
  └─ [3] Clicks "GitHub" (Actions Tab)
      └── POST http://<PC_IP>:8000/operator/action { "action": "open_site", "payload": { "site": "github" } }
```

## Wireframes

### Home Tab
Displays the greeting, current focus, current project, pending tasks count, and an active connection health indicator (showing latency to the PC). It includes 3 large buttons:
- Trigger Morning Brief
- Trigger Resume Session
- Trigger Analyze Screen

### Actions Tab
A 2-column grid of "Quick Links" that mirror the most commonly used tools on the PC. Clicking them sends an `open_site` command to the PC.
- GitHub, LinkedIn, ChatGPT, Claude, Notion, LeetCode.

### Settings Tab
A simple configuration screen to store the PC's local IP address and future-proof toggles (Dark Mode, Auto Connect, and disabled integrations like Hardware Bridge).

## Setup Instructions

Because the companion is built in Flutter, you must compile it onto your device:

1. Install [Flutter SDK](https://docs.flutter.dev/get-started/install).
2. Open a terminal and navigate to the companion directory:
   ```bash
   cd android_companion
   ```
3. Fetch dependencies:
   ```bash
   flutter pub get
   ```
4. Connect your Android device via USB (or start an emulator) and run:
   ```bash
   flutter run
   ```
5. Once the app opens, go to the **Settings** tab and enter your PC's local IP address (e.g., `192.168.1.100:8000`).
6. The Home tab will show 🟢 Connected.
