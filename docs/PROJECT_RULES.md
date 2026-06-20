# Project Rules

1. **Never duplicate systems**: Do not rewrite existing functional core systems. Wrap them, extend them, or interface with them instead.
2. **Reuse existing code**: Leverage the existing components such as the FastAPI setup, Groq API implementations, and TTS/STT pipelines.
3. **Prefer modularity**: Break down large functions and monolith files. Keep concerns separated.
4. **Avoid giant files (>500 lines)**: No more monolithic `main.py` files. Move specific routes and middleware into appropriate modules.
5. **Separate concerns**: Ensure the routing logic (Brain), execution logic (Tasks), and memory logic (Vector Store) are decoupled and communicate through clear interfaces.
6. **No hardcoded values**: Use configuration files (`configs/`) and environment variables. Do not hardcode API keys, system prompts, or application limits in the Python code.
7. **Always document new systems**: Ensure all newly added systems are thoroughly documented in `docs/` and have inline docstrings for complex logic.
8. **Preserve backward compatibility**: New updates must not break existing features, especially the core SSE streaming, TTS functionality, or the frontend.
9. **Every system should be replaceable**: Design components behind interfaces so that any service (e.g., swapping Groq for Ollama) can be substituted easily.
10. **Build for scalability**: Assume this application will run not just locally but potentially manage distributed systems. Think like an architect designing an Operating System, not just an MVP application.
