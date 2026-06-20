# Identity Engine

## Responsibilities
The Identity Engine is responsible for ingesting, validating, and managing the user's global profile. It serves as the single source of truth for "Who is the Boss".

## Inputs
* **JSON Profiles**: Reads from the `profiles/` directory, including goals, projects, preferences, relationships, and the core profile.

## Outputs
* **`get_identity_context()`**: Outputs a unified, structured Python dictionary containing the most relevant identity data (name, active projects, goals, preferences, and devices) to be consumed by the Brain.

## Future Usage
In later phases, the Identity Engine will dynamically observe user behavior and automatically update the JSON profiles. It will be the foundation for hyper-personalization, allowing the OS to alter its tone, priorities, and workflow suggestions based on the user's explicit and implicit preferences.
