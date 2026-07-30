# JARVIS Desktop Audit: Settings Report (SETTINGS_REPORT.md)

## 1. Executive Summary
This report audits configuration persistence, default values, migration safety, and `QSettings` read/write operations.

---

## 2. Settings Registry & Persistence Matrix

| Setting Key | Type | Default Value | Storage Domain | UI Binding Component |
| :--- | :--- | :--- | :--- | :--- |
| `launch_at_startup` | `bool` | `False` | `QSettings` / Registry | `SettingsDialog` toggle & `StartupManager` |
| `start_minimized` | `bool` | `False` | `QSettings` | `SettingsDialog` toggle |
| `hotkey` | `str` | `"Ctrl+Space"` | `QSettings` | `GlobalHotkeyManager` |
| `hud_opacity` | `float` | `0.95` | `QSettings` | `OverlayManager` |
| `notification_sounds`| `bool` | `True` | `QSettings` | `NotificationService` |
| `auto_activity` | `bool` | `True` | `QSettings` | `SettingsDialog` toggle |
| `auto_search` | `bool` | `True` | `QSettings` | `SettingsDialog` toggle |
| `thinking_sounds` | `bool` | `True` | `QSettings` | `SettingsDialog` toggle |
| `voice_interrupt` | `bool` | `True` | `QSettings` | `SettingsDialog` toggle |
| `window/pos` | `QPoint` | Dynamic | `QSettings` | `WindowManager` / `SettingsManager` |
| `window/size` | `QSize` | `1280x800` | `QSettings` | `WindowManager` / `SettingsManager` |
| `window/mode` | `str` | `"jarvis"` | `QSettings` | `HeaderBar` mode selector |

---

## 3. Findings
- **Persistence Verification**: Tested and verified. Settings save on edit and reload automatically upon application restart.
