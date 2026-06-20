# Verifier Engine

The Verifier Engine sits at the end of the Cognitive Pipeline. It evaluates the outcome of the `Executor` using deterministic, rules-based logic to determine the success or failure of an action. 

It does **not** rely on AI for decision-making. Instead, it processes execution state flags to decide the final disposition.

## Responsibilities
- **Input**: The planned action, the executor's result, and the original decision context.
- **Output**: A `VerificationResult` indicating the final status.
- **Statuses**: `success`, `partial_success`, `failure`, `retry`, `cancel`.

## Core Rules
- If required data missing → **fail**
- If dependencies unresolved → **retry**
- If action completed → **success**
- If timeout → **retry**
- If retries exceeded → **cancel**
