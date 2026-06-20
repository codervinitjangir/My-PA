# Jarvis Dashboard Module

The Dashboard module is responsible for providing the instantaneous "Home Screen" state when the user opens the JARVIS UI.

## Performance Requirements
- **NO LLM CALLS**: All summarization and logic MUST be purely programmatic rules.
- **SPEED**: Must return the full JSON payload in `<100ms`.
- **DATA**: Data is sourced exclusively from the `GlobalStateManager`.
