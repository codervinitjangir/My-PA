# Digital Activity Awareness

The **Digital Activity Awareness** module allows JARVIS to understand what the Boss is doing digitally without breaking absolute system rules.

## Core Philosophy
The browser is only one signal among many. True digital awareness comes from aggregating multiple passive sources. This module adheres to the following constraints:
- **READ ONLY**: No actions are taken on the user's behalf.
- **No Browser Control**: We do not inject scripts or automate browsers (No Selenium, Playwright, Puppeteer).
- **No Input Monitoring**: Keyloggers and mouse trackers (`pyautogui`, `keyboard`) are strictly banned.
- **High Performance**: No LLMs or Groq calls are used to infer activity. Everything executes in `<50ms` using deterministic rules.

## Signals Analyzed
The `DigitalObserver` combines:
1. `active_window_title` (e.g., "GitHub - Google Chrome")
2. `running_processes` (e.g., `["Code.exe", "msedge.exe"]`)
3. `active_session` (From the Session Engine)
4. `active_project` (From Global State)

## Focus Drift Detection
By cross-referencing the inferred activity with the user's active session or project, JARVIS can determine if focus is maintained.
- **Example 1**: Active session is "Jarvis OS Refactoring" + Activity is `Building` = `Focus Drift: False`.
- **Example 2**: Active session is "Jarvis OS Refactoring" + Activity is `Entertainment` (e.g., YouTube) = `Focus Drift: True`.
