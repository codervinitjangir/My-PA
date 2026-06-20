# Engineering Guidelines

## Folder Conventions
* **`core/`**: Critical system initialization, logging, and core loops.
* **`brain/`**: The central routing and decision-making logic.
* **`memory/`**: Vector store, short-term session storage, and semantic retrieval logic.
* **`planner/`**: Agentic planning, loop unrolling, and reasoning frameworks.
* **`executor/`**: Action execution logic, separated from planning.
* **`agents/`**: Specialized agent definitions (e.g., coding agent, research agent).
* **`devices/`**: Hardware and API protocols to communicate with external systems.
* **`autonomy/`**: Background loop logic that triggers tasks independently of user input.

## Naming Conventions
* **Python Modules**: `snake_case`
* **Classes**: `PascalCase`
* **Functions/Variables**: `snake_case`
* **Constants**: `UPPER_SNAKE_CASE`
* **JSON Configs**: Use templates with `snake_case` keys.

## Service Conventions
* **Dependency Injection**: Services should be decoupled and injected. A service should not instantiate another service internally if it can be avoided.
* **Single Responsibility**: Each service handles one domain (e.g., `TTS_Service` only generates audio).

## Dependency Conventions
* Avoid adding large dependencies unless absolutely required.
* Keep `requirements.txt` updated.
* Ensure all async/await loops are properly managed without blocking threads.

## Documentation Rules
* Use standard Google Python Style docstrings for methods.
* Update architecture diagrams (Mermaid) when significant changes are made.
* Keep `README.md` and specific system docs up to date.
