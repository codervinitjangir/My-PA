# Context Engine

## Purpose
The Context Engine represents the nervous system and awareness layer of Jarvis OS. 
It answers four fundamental questions:
1. Who is Boss?
2. What is Boss doing?
3. What matters now?
4. What should Jarvis focus on?

## Modules
* **Context Manager**: The main orchestrator.
* **Context Builder**: Constructs the structured context output including heuristic focus detection.
* **Context Prioritizer**: Ranks items based on urgency (e.g., today, tomorrow, deadlines).
* **Context Filter**: Applies expiration rules (e.g., sessions expire after hours, interviews expire after events).
* **Context Observer**: Passively listens for new goals, memories, and profile updates without taking action.
