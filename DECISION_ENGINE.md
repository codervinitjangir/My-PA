# Decision Engine

## Responsibilities
The Decision Engine represents the "free will" layer of Jarvis OS. It answers a single question: "What should happen next?" 
It sits above the Integration Layer and reads the Unified Context to determine if Jarvis should passively observe, actively plan a goal, execute a pending action, or wait to avoid interrupting the user.

## Inputs
* **DecisionContext**: A struct containing the Identity, Memory, active goals, priority items, and current focus, extracted from the Integration Manager.

## Outputs
* **Decision**: A structured intent object detailing exactly what category of action to take (e.g., `PLAN`, `WAIT`, `SUGGEST`), the confidence of that decision, and the explicit reason for it.

## Architecture
1. **Decision Rules**: Deterministic `if/else` evaluations applied to the context.
2. **Decision Evaluator**: Applies all rules to generate a list of potential `DecisionCandidate`s.
3. **Decision Selector**: Takes the list of candidates and selects the single absolute best action based on priority sorting and confidence metrics.
4. **Decision History**: Logs the chosen decision and the "reason" string to an internal array to track behavioral logic over time.

## Future Integrations
In the next phase (Autonomy), a background event loop will run every few seconds. It will pull the Context, feed it to the Decision Engine, and then route the output. For example, if the Decision Engine outputs `PLAN`, the Autonomy loop will trigger the `Planner Engine` to spin up tasks without the user ever typing a prompt. If it outputs `WAIT` (because the user is coding), the Autonomy loop will sleep.
