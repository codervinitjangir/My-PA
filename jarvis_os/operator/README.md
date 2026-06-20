# Operator Engine

The Operator Engine acts as the central conductor for JARVIS OS. It does **not** process intelligence or execute actions; instead, it routes requests to the appropriate dedicated sub-systems.

## Constraints
- **Not an Agent**: It does not "think" or hallucinate routing logic. It relies on strict keyword deterministic routing.
- **No Autonomy**: It routes execution requests to `desktop_action`, but does not bypass the necessary safety and permission locks.
