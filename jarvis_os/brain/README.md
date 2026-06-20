# Brain Foundation

## Purpose
The Brain Foundation is the cognitive core of Jarvis OS. It does not generate responses (which is handled by the Executor/Agent layers). Instead, it understands the user, fetches memories, builds the active context, and prioritizes what Jarvis should care about.

## Responsibilities
* Observe inputs.
* Understand intents based on global identity.
* Prioritize internal tasks.
* Prepare the unified Context block (`build_brain_context()`).

## Current State (Week 1 Part 2)
Foundation built. The `build_brain_context()` function successfully aggregates data from the Identity and Memory engines. It is not yet connected to the Groq APIs.
