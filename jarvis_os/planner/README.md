# Planner Engine

## Purpose
The Planner Engine provides Jarvis with the cognitive capability to break high-level, complex objectives into small, actionable steps. It converts abstract desires ("Help me apply for jobs") into a deterministic, sequential to-do list.

## Responsibilities
* Parse natural language into structured `Goal` objects.
* Decompose `Goal`s into sub-components (`Task`s).
* Generate deterministic execution sequences (`Plan`s).
* Assign strict priorities to plans and tasks based on keyword heuristics.

## Constraints
Currently (Week 2 Part 1), the Planner relies strictly on hardcoded heuristics. There is no AI involved. This guarantees stable architecture and dependency flows before plugging in an LLM agent to do the decomposition dynamically.
