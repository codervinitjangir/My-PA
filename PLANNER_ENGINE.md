# Planner Engine

## Responsibilities
The Planner Engine is responsible for breaking down high-level, natural language goals into a structured, sequential list of executable tasks. It is the logical reasoning block that sits between the Brain (understanding what to do) and the Executor (actually doing it).

## Inputs
* **Natural Language Goals**: E.g., "Help me apply for internships" or "Let's code the new feature."

## Outputs
* **`Plan` Object**: A highly structured object containing an ordered list of `Task` objects, complete with dependencies, priorities, and statuses.

## Architecture
1. **Goal Parser**: Cleans the input string and formats it into a `Goal`.
2. **Task Decomposer**: Splits the `Goal` into smaller `Task` items. (Currently uses rule-based heuristics).
3. **Plan Generator**: Wires the `Task`s together sequentially with simulated dependencies.
4. **Plan Prioritizer**: Scans the text for urgency keywords to classify the plan's priority (Critical, High, Medium, Low).
5. **Planner Manager**: The unified interface that runs the pipeline end-to-end.

## Future Integrations
In the future, the **Task Decomposer** will be upgraded from simple Python `if/else` rules to an LLM-driven process. The Brain will pass the `build_ai_context()` string alongside the Goal to an Agent, allowing the Planner to generate highly contextual, dynamic task lists. The completed `Plan` will then be handed off to the future `Executor Engine` for actual execution.
