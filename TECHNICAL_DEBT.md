# Technical Debt Report

## Current Bottlenecks
1. **API Rate Limiting**: The system relies heavily on Groq. While fallback keys exist, rapid multi-agent requests in the future will easily exhaust the RPM (Requests Per Minute) limits.
2. **Synchronous TTS Blocking**: The Edge TTS generation runs in a ThreadPool but effectively blocks the initial chunk streaming until the first full sentence is formed, adding 300-800ms of latency before audio begins.
3. **Monolithic Frontend**: `script.js` exceeds 1500 lines and combines state management, UI rendering, Web Audio API queueing, and SSE parsing.
4. **Monolithic Backend**: `main.py` is over 800 lines and combines routing, SSE generation, and FastAPI middleware.

## Risks
1. **Memory Exhaustion**: The FAISS vector store loads the entire `learning_data/` directory into RAM on startup. As the personal knowledge base grows into gigabytes, this will crash the server.
2. **Thread Starvation**: Extensive use of `ThreadPoolExecutor` for background tasks, TTS, and API calls could exhaust system threads during heavy concurrent usage.

## Single Points of Failure
1. **Groq API**: If the Groq API is inaccessible, the system's Brain, Chat, and Tasks fail completely. There is no local offline fallback.
2. **Pollinations API**: Image generation will hang and timeout if Pollinations goes down, as there is no timeout wrapping the synchronous `httpx` call.
3. **Vanilla JS VAD**: If the browser's Web Audio API context suspends (common in modern browsers), the microphone Voice Activity Detection will silently fail.

## Scalability Issues
1. **Stateless Services**: Services currently rely on in-memory dictionaries for active sessions, preventing horizontal scaling across multiple workers or servers.
2. **Coupled Intent Classification**: The "Brain" is hardcoded to a strict set of rule-based intents (`open`, `play`, `generate_image`). Adding new tools requires modifying regex and core system prompts.

## Suggested Fixes
1. **Decoupling**: Move logic from `main.py` into the new OS-level folders (`brain/`, `executor/`).
2. **Agentic Tool Use**: Replace hardcoded `BrainService` intents with LangChain/LangGraph Tool Calling, allowing dynamic addition of capabilities.
3. **Local Fallback**: Integrate a local model (e.g., Ollama 8B) for intent classification and fallback conversation if Groq fails.
4. **Database Migration**: Move from in-memory session dictionaries to Redis or SQLite to allow multi-worker scaling.
5. **Frontend Rewrite**: Port the Vanilla JS to a component-based framework (React/Vue) and offload audio/VAD processing to a Web Worker.
