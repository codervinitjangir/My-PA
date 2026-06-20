# JARVIS Observers

The `observers/` directory contains read-only modules designed to grant JARVIS digital awareness without automation or control capabilities.

## Philosophy
- **Read Only**: Observers ONLY collect signals. They do NOT act.
- **No Automation**: We do not use Selenium, Playwright, or Puppeteer.
- **No Extensions**: We do not inject JavaScript or rely on browser extensions.
- **Performance**: All observers must execute in `<50ms`. No LLMs or Groq calls are permitted in the critical observation path.

## Digital Observer
The `digital_observer.py` infers the current Digital Activity of the user (e.g., Building, Learning, Job Search) based on:
- Active window titles (via OS APIs)
- Running processes
- JARVIS's internal active session and project context

### Focus Drift
By comparing the inferred activity with the user's active session, the Digital Observer can detect **Focus Drift** (e.g., watching YouTube while a coding session is active).
