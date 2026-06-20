# Executor Foundation

## Purpose
The Executor Engine bridges the gap between Planning and Action. It receives a structured `Plan` from the Planner Engine and converts it into a series of manageable, trackable `Action`s. It does **not** actually execute physical code, API calls, or browser controls itself—it is strictly the managerial organ that tracks state, dependencies, and retries.

## Components
* **ActionQueue**: Holds all actions and manages their states (`pending`, `ready`, `running`, `completed`, `failed`, `cancelled`).
* **ActionDispatcher**: Translates Planner `Task`s into Executor `Action`s.
* **ActionScheduler**: Determines which action is allowed to run next based on dependencies, priority, and FIFO logic.
* **ExecutionTracker**: Records timestamps, durations, errors, and handles backoff retry logic (1s, 2s, 5s).
* **ExecutorManager**: The master interface for the layer.

## Future Usage
In later phases, once an action is marked `ready` by the `ActionScheduler`, the `ExecutorManager` will hand it off to a specific Agent (e.g., the Coder Agent or Browser Control Agent). If the agent fails, the `ExecutionTracker` will issue a retry command according to the backoff schedule. 
