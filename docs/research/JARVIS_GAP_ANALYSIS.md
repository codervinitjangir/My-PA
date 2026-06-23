# JARVIS Gap Analysis

## 1. Current Architecture vs Ideal Architecture

### Current Architecture
Currently, JARVIS is structured as a tight coupling between a FastAPI web layer (`app/`) and an OS abstraction layer (`jarvis_os/`).
- **Core Intelligence**: `brain_service.py`, `chat_service.py`, `groq_service.py`, `realtime_service.py`.
- **Integrations**: Hardcoded directly into services or `desktop_action_manager.py`.
- **Routing**: Handled by a massive `app/main.py` and `request_router.py`.

### Ideal Architecture (CTO Target)
A highly modular, layered system where the core intelligence is decoupled from the execution environment:
```text
core/
├── orchestrator/ (Replaces BrainService routing)
├── agents/ (Specialized workflows: Coding, Research, General)
├── memory/ (Unified FAISS + Profile storage)
├── tools/ (Dynamic registry of capabilities)
├── providers/ (Base provider, Groq, Ollama, etc.)
└── automations/ (Background scheduled tasks)
```

## 2. Duplicate Systems Detection
- **GroqService vs RealtimeGroqService**: Both implement LLM calls using Groq. The only difference is the injection of Tavily search tools. *Action*: Merge into a single `GroqProvider` that accepts a list of dynamic tools.
- **TaskExecutor vs TaskManager**: `TaskExecutor` handles the AI generation of a plan, while `TaskManager` executes python functions in the background. Naming is confusing and functionality slightly overlaps.
- **Action/Capability Registries**: `jarvis_os/core/capability_registry.py` and `jarvis_os/desktop_action/desktop_action_manager.py` have overlapping responsibilities regarding what the system can do.

## 3. Missing Systems
- **Provider Abstraction**: Hardcoded to `langchain-groq`. If Groq goes down, JARVIS goes down. Needs a `providers/` layer.
- **Unified Tool Registry**: Tools are currently scattered as Python functions inside `desktop_action_manager` or LangChain tools in `realtime_service.py`.
- **Robust Agent Orchestrator**: The current `BrainService` acts as a simple classifier (router) rather than a true multi-agent orchestrator that delegates sub-tasks.
- **Model Context Protocol (MCP)**: Missing support for standard MCP tools.

## 4. Weak Systems
- **`app/main.py`**: At over 1,100 lines, it handles FastAPI setup, middleware, state management, TTS streaming logic, and websocket-like events. This is a massive bottleneck for maintainability.
- **Memory Architecture**: The current FAISS implementation works, but lacks semantic garbage collection, deduplication, and a robust user-profile memory abstraction (it's currently a flat vector space).

## 5. Technical Debt
- **Direct LLM Calls in OS Layer**: `jarvis_os/observers/screen_observer.py` directly instantiates `VisionService`. The OS layer should ideally publish an event, and the Intelligence layer should handle the LLM call.
- **Dead/Experimental Code**: The `/archive/` folder indicates leftover code. 
- **TTS Streaming Tight Coupling**: The custom TTS chunking logic in `main.py` (`_stream_generator`) is highly complex and tightly coupled to the HTTP response cycle.

## 6. Summary of Gaps
JARVIS excels at being a fast, integrated desktop assistant, but its internal intelligence layer is too monolithic. The biggest gap is the lack of a **Provider Abstraction** and a **Dynamic Tool Registry**. Fixing these two areas will yield the highest return on investment.
