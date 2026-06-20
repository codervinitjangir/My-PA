# Session Intelligence Engine

This module transforms JARVIS from a stateless entity into a persistent working companion. It organizes tasks, tracks focus, and resumes state seamlessly across work days.

## Capabilities
- Tracking and restoring active `WorkSession` data structures.
- Summarizing current focus, pending tasks, and completed tasks.
- Non-AI, deterministic resume logic (e.g. mapping "yesterday" to the latest session from the previous calendar day).

## Absolute Directives
This is **NOT** a memory engine or an autonomous agent. It does not "think". It strictly maps human inputs into defined JSON schemas and returns them on command.
