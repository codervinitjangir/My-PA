# Cognitive Pipeline

The Cognitive Pipeline acts as the central nervous system for JARVIS OS. It connects all independent cognitive engines (organs) into a single, cohesive thinking loop.

## Pipeline Order
1. **Identity**: Establishes who JARVIS is right now.
2. **Memory**: Retrieves relevant past context and knowledge.
3. **Context**: Fuses Identity, Memory, and the immediate situation.
4. **Decision**: Determines *what* to do based on Context.
5. **Planner**: Determines *how* to do it.
6. **Executor**: Carries out the plan (Simulated in this sprint).
7. **Verifier**: Deterministically evaluates the Executor's outcome.

## Operations
- Uses `run_cognitive_cycle()` to execute a goal through the pipeline.
- Currently operates in **Simulation Mode** (does not execute real code or connect to external AIs).
