# JARVIS Workspaces

The `workspaces/` directory manages the overarching contexts of Boss's digital life.

## Philosophy
- **Organization over Intelligence**: Workspaces are organizational containers, not AGI agents. They group related tools, sessions, and tasks to reduce mental load.
- **Fast Context Switching**: By isolating "what matters now", Boss can switch from `Jarvis` mode to `Career` mode instantly, filtering out irrelevant noise.
- **Performance**: Inferring the suggested workspace based on `DigitalActivity` and `Session` data takes `<50ms` and uses no LLMs.

## Key Components
- `workspace_models.py`: Defines the `Workspace` container.
- `workspace_manager.py`: Deterministically infers the current and suggested workspace.
- `workspace_builder.py`: Aggregates the relevant global state to populate a Workspace object.
