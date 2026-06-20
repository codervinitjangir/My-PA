# JARVIS Command Center

Built during the **Final Polish Sprint**.

## Philosophy

The Command Center is the single point of entry for all major JARVIS capabilities. Previously, Boss had to navigate through the dashboard or chat to find buttons. Now, all core actions are unified at the very top of the UI.

## The 7 Actions

1. 🌅 **Morning Brief** — Fetches the daily brief and shows the sub-panel.
2. ▶ **Resume Session** — Sends the resume command to the chat interface.
3. 👁 **Analyze Screen** — Triggers the new Screen Awareness capture without leaving the dashboard.
4. 💻 **Open Workspace** — Opens VS Code directly.
5. 🌐 **Quick Links** — Smooth scrolls to the Quick Links section.
6. 📝 **Add Friction** — Smooth scrolls to and focuses the friction log input field.
7. 🔄 **Refresh** — Invalidates the dashboard cache and redraws the UI.

## UI Decisions

- **No AI:** Buttons are purely frontend triggers. They call existing JavaScript functions.
- **Large Target Area:** CSS Grid with `minmax(180px, 1fr)` ensures buttons are large and easy to hit on both desktop and mobile.
- **No Animations:** Buttons use a simple CSS transform and hover state to maintain a fast, snappy feel. No complex glassmorphism beyond the existing panel style.

## Why This Matters

Muscle memory. Boss no longer needs to hunt for the right button. Top of the screen, big targets, one click.
