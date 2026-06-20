# JARVIS Core

The `core` module establishes the non-negotiable structural interfaces of JARVIS OS. By enforcing universal contracts (`CapabilityInterface`), it enables the Operator to dynamically route, execute, and pull state from any capability without hardcoding custom logic.

## Directives
- **Simplicity Over Everything**: Do not add bloated adapters here. Interfaces must remain exactly as defined: `initialize`, `health`, `get_state`, `execute`, `shutdown`.
- **Global State**: The `GlobalStateManager` creates the single source of truth for the LLM to parse. Never build parallel state aggregators outside of this component.
