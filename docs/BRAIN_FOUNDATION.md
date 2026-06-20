# Brain Foundation

## Responsibilities
The Brain acts as the cognitive orchestrator. It does not generate text for the user; instead, it observes inputs, understands context by querying the Identity and Memory engines, and prioritizes active tasks.

## Inputs
* **Session Data**: Ephemeral context regarding the current interaction.
* **Identity Context**: Pushed from the `IdentityManager`.
* **Recent Memories**: Pushed from the `MemoryManager`.

## Outputs
* **`build_brain_context()`**: Produces a massive, structured Context block that contains everything Jarvis needs to know about the user, their goals, and their past before it ever makes an API call.

## Future Usage
The Brain Foundation will eventually drive the autonomous loops. By constantly evaluating `active_goals` and `active_projects` against the `prioritizer`, the Brain will be able to wake up, execute background research or system tasks, and present the user with completed work without the user explicitly asking for it.
