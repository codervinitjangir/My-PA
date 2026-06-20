# Integration Layer

## Purpose
The Integration Layer acts as the bridge connecting the foundational systems (Identity, Memory, Context) into a clean interface. It prevents the existing FastAPI application (`jarvis/app/`) from needing to understand the complex internal OS logic.

## Adapters
* **`identity_adapter.py`**: Condenses massive JSON profiles into core identity metrics.
* **`memory_adapter.py`**: Enforces rules to only fetch high-priority, relevant memories, protecting token limits.
* **`context_adapter.py`**: Fuses data into the Unified `jarvis_state`.
* **`brain_adapter.py`**: Formats the `jarvis_state` into a concise string (`build_ai_context()`) for LLM consumption.

## Future Integration Points

### Current BrainService
In the future, `brain_service.py` in the MVP will call `IntegrationManager.build_ai_context_string()` and prepend it to its system prompt before classification or chat.

### Future Planner
The Planner will consume the entire raw dictionary from `build_jarvis_state()` to make autonomous decisions on background loop execution.

### Future Agents
Agents (like the Researcher or Coder) will pull specific slices of the `jarvis_state` (e.g., coding preferences) via the adapters.

### Future Device Layer
The Device Layer will report its state back into the `ContextManager` through this integration bridge.

### Future Autonomy
Background polling loops will check `build_jarvis_state()` for active goals and priorities when deciding if the OS should wake up and perform a task unprompted.
