# Context Engine

## Responsibilities
The Context Engine acts as the awareness layer and nervous system of Jarvis OS. Its primary responsibility is to maintain an up-to-date representation of what the user is currently doing and what matters most at the present moment.

## Components
* **Context Manager**: Orchestrates the flow of data across the other context modules.
* **Context Builder**: Constructs the final `current_context` dictionary, fusing identity, memory, and active session data, and infers the user's current focus.
* **Context Prioritizer**: Ranks context items (memories, goals, projects) by importance (e.g., today, tomorrow, deadlines).
* **Context Filter**: Applies expiration rules (e.g., sessions expire after a few hours, interviews expire after the event) to prevent context bloat.
* **Context Observer**: Passively monitors incoming data (new memories, goals, etc.) without triggering autonomous execution.

## Inputs
* The Identity Engine (`IdentityManager`)
* The Memory Engine (`MemoryManager`)
* Live session data (chat history, current environment state)

## Outputs
* **`get_awareness_context()`**: Outputs a heavily filtered, prioritized, and focused JSON object representing the exact state of the user's world right now.

## Future Integrations
The Context Engine will be integrated with the autonomous Planner. When the Observer detects a high-priority context shift (e.g., an urgent email arrives), it will pass the updated context object to the Planner, which may decide to interrupt the user or spawn a background task.
