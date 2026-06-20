# Runtime Engine

The Runtime Engine handles the final assembly of JARVIS OS contextual state just before answer generation. It guarantees a highly compact, token-safe string (400-500 words max) explicitly designed to enrich LLM prompt construction without incurring heavy latency or context limit breaks.

## Key Principles
- **No Heavy Operations**: The runtime operates locally, aggregating state without blocking.
- **Selective Exposure**: It prioritizes `current_focus`, `active_goals`, `active_projects`, `top_memories`, and `current_priorities`.
- **Token Safety**: Truncates any context that bleeds over 500 words.
