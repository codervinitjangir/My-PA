# Workspaces

The **Workspace System** organizes Boss's digital life into overarching contexts. 

## Core Philosophy
A Workspace is not an intelligent agent. It is an organizational container. It reduces mental load by encapsulating the tools, sessions, and tasks relevant to a specific domain (e.g., `Career`, `Vision`, `Jarvis`). 

When a Workspace is active, Boss only sees the `pending_items` and `sessions` relevant to that world. 

## Automated Suggestions
To prevent the friction of manually switching contexts, the `WorkspaceManager` continuously infers the **Suggested Workspace** based on existing passive signals.
- **Rule Example**: If the `DigitalObserver` detects `ActivityType.JOB_SEARCH` (e.g., LinkedIn is active), the manager suggests switching to the `Career` workspace.
- **Performance**: This inference is completely deterministic, utilizing zero LLM overhead, and executing in `<50ms`.

## Integration
Workspaces act as a high-level filter for the existing JARVIS systems:
- **Dashboard**: The dashboard UI explicitly states the `Current Workspace` to ground the user.
- **Session Engine**: Workspaces contain many sessions.
- **Timeline**: Events are tagged by their active Workspace context.
