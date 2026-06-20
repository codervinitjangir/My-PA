# Self Awareness Layer

The Self Awareness Layer is the final intelligence organ of JARVIS OS before abilities are enabled. It provides JARVIS with an introspective and contextual understanding of the overarching environment and the user's ("Boss") active state.

## Core Responsibilities
- **Understand the User**: Who is Boss, what are they working on, what is urgent?
- **Observe Changes**: Passively monitors project, goal, and memory shifts.
- **Generate Suggestions**: Uses a strict rules-engine (No AI) to recommend actions or enforce non-interruption protocols (e.g., during active coding sessions).

## Components
- `awareness_manager.py`: Orchestrator of the awareness pipeline.
- `awareness_builder.py`: Structures the strict `{boss_state, active_projects, ...}` schema.
- `awareness_suggester.py`: Deterministic rules engine mapping specific conditions to suggestions.
- `awareness_monitor.py`: Passive observer logging state deltas.
