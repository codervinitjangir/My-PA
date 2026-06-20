# JARVIS OS - Architecture Diagram (Milestone Beta Part 1)

```mermaid
graph TD
    User([User Request via Frontend])
    FastAPI[FastAPI Endpoints<br>app/main.py]
    
    Router{RequestRouter<br>jarvis_os/core/request_router.py}
    FeatureFlag{{.env<br>ENABLE_OPERATOR_RUNTIME}}
    
    LegacyChatService[ChatService<br>app/services/chat_service.py<br>(LEGACY)]
    
    OperatorRuntime[OperatorRuntime<br>jarvis_os/core/operator_runtime.py<br>(CEO)]
    GlobalState[GlobalStateManager<br>jarvis_os/core/global_state.py]
    
    CapSession[Session]
    CapAwareness[Awareness]
    CapComputer[Computer]
    CapIdentity[Identity]
    
    GroqService[GroqService<br>Reasoning Engine]
    Response([Final Response])

    User --> FastAPI
    FastAPI --> Router
    Router --> FeatureFlag
    
    FeatureFlag -->|False| LegacyChatService
    LegacyChatService -.-> GroqService
    
    FeatureFlag -->|True| OperatorRuntime
    
    OperatorRuntime -->|1. Request State| GlobalState
    GlobalState -->|Pulls Data| CapSession & CapAwareness & CapComputer & CapIdentity
    GlobalState -->|Returns Aggregate| OperatorRuntime
    
    OperatorRuntime -->|2. Send Context + User Intent| GroqService
    
    GroqService -->|3. Formatted Response| OperatorRuntime
    OperatorRuntime --> Response
    LegacyChatService -.-> Response
```

## Key Changes
1. **Request Router**: A dedicated interception layer has been added before any business logic executes. It checks `ENABLE_OPERATOR_RUNTIME`.
2. **Untouched Legacy**: `ChatService` and `BrainService` are preserved exactly as they were. If the feature flag is false, the system behaves exactly like the original JARVIS.
3. **Operator Runtime**: Takes full control over context generation by polling the capability modules via `GlobalStateManager`, bypassing the old `ChatService` context builder entirely.
