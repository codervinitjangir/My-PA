# J.A.R.V.I.S Desktop User Guide (v1.0 RC1)

Welcome to **J.A.R.V.I.S Desktop**, a native Windows AI assistant built with PySide6. JARVIS lives in your Windows System Tray and responds instantly anywhere on your system via global hotkeys and voice overlays.

---

## 1. Quick Start

### Global Hotkey (`Ctrl + Space`)
Press **`Ctrl + Space`** anywhere in Windows to summon the **Raycast Command Palette**.
- Type actions: `Open VS Code`, `Morning Brief`, `Analyze Screen`, `Search Memory`.
- Use **`Up`** and **`Down`** arrows to navigate, **`Enter`** to execute, or **`ESC`** to dismiss.

### System Tray Application
JARVIS runs silently near your Windows clock:
- **Badge Colors**:
  - 🟣 **Purple**: Idle & Online
  - 🔵 **Blue**: Listening to Voice Input
  - 🟢 **Green**: Executing Action / Streaming
  - ⚪ **Gray**: Offline / Reconnecting
- Right-click the **`J`** icon to access:
  - `Open Dashboard`
  - `Quick Chat`
  - `Reconnect Backend`
  - `Restart Services`
  - `Settings`
  - `Exit JARVIS`

---

## 2. Floating Overlays & Voice HUD

When you activate voice commands or trigger actions, a frameless glass pill overlay appears at the top of your screen:
- **🎤 Listening...**: Recording user voice input.
- **🧠 Thinking...**: LLM routing & token processing.
- **🔊 Speaking...**: Voice synthesis playback (Barge-in supported).
- **⚡ Executing...**: Desktop automation task running.
- **✓ Completed**: Action finished (auto-dismisses in 3s).

---

## 3. Keyboard Shortcuts

| Shortcut | Description |
| :--- | :--- |
| **`Ctrl + Space`** | Summon / Dismiss Command Palette |
| **`Enter`** | Send message / Execute selected command |
| **`Shift + Enter`** | Multiline text entry |
| **`ESC`** | Close Command Palette or Settings Overlay |
