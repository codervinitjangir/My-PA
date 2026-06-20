# OPERATOR ACTIVATION

## What Changed
- **Request Router**: Introduced a dedicated interception layer in `main.py` to transparently route FastAPI requests depending on the `.env` flag `ENABLE_OPERATOR_RUNTIME`.
- **Operator Runtime**: Established the new "CEO" of the system, which directly calls `GlobalStateManager` and `OperatorRouter` before formatting the response via Groq.
- **Global State Builder**: Developed `build_global_state()` to replace the disparate context strings from the legacy `chat_service.py` with a single structured payload aggregating all capability departments.

## What Stayed Untouched
- **FastAPI Endpoints**: The `@app.post("/chat")` endpoints remain identical.
- **Frontend / Streaming**: The frontend still receives the exact same standard response strings.
- **BrainService**: Remained completely untouched and is now structurally independent of the new Operator routing path, acting as a fallback or future Intent Classifier.

## Data Flow
```text
User Input -> FastAPI -> RequestRouter -> (if enabled) -> OperatorRuntime -> GlobalState -> Groq -> User
```

## Rollback Procedure
If the Operator encounters an unhandled exception or breaks:
1. Open `.env`.
2. Change `ENABLE_OPERATOR_RUNTIME=true` to `ENABLE_OPERATOR_RUNTIME=false`.
3. Restart the server. 
4. The system will instantly revert to executing via `ChatService` and `BrainService`.
