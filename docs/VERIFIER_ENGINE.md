# Verifier Engine

The **Verifier Engine** is the final component of the JARVIS OS Cognitive Pipeline. Its sole responsibility is to evaluate the output of the Executor Engine and deterministically decide the ultimate success, failure, or retry status of the cognitive cycle.

## Architecture & Responsibilities
- **Input**: The planned action, the executor's result, and the original decision context.
- **Output**: A `VerificationResult` indicating `success`, `partial_success`, `failure`, `retry`, or `cancel`.
- **Rules Engine**: Operates purely on deterministic rules—NO AI or LLM evaluation is used at this stage.

## Execution Flow

```mermaid
graph TD
    A[Executor Result] --> B{Apply Rules}
    
    B -->|retries_exceeded == True| C[CANCEL]
    B -->|missing_data == True| D[FAILURE]
    B -->|unresolved_dependencies == True| E[RETRY]
    B -->|timeout == True| F[RETRY]
    B -->|completed == True| G{Warnings?}
    
    G -->|Yes| H[PARTIAL_SUCCESS]
    G -->|No| I[SUCCESS]
    
    C --> J((Log Verification))
    D --> J
    E --> J
    F --> J
    H --> J
    I --> J
```

## Future Integrations
- Can be expanded with complex, non-AI programmatic rules based on system logs, return codes, and database states.
- Can connect back to the Context Engine to provide feedback loops for future decisions.
