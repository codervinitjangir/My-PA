# Borrow vs Build Strategy

This report evaluates key subsystems within JARVIS against the broader open-source ecosystem, advising whether to keep, improve, build, or borrow implementations.

| Subsystem | Current Implementation | Score (1-10) | Build Ourselves? | Borrow from Another Repo? | Recommendation | Priority |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- |
| **Memory Systems** | Local FAISS vector store. No discrete profile system. | 6 | **Yes**. RAG is highly specific to personal OS contexts. | Borrow from *Mem0* or *Zep* for concepts, but don't import them. | **Improve**. Refactor current FAISS logic into a structured `memory/` module supporting Profiles and Projects. | Medium |
| **Agent Orchestration** | Hardcoded `BrainService` routing to `TaskExecutor`. | 4 | **Yes**. Our workflow needs to be tight and fast. | Borrow logic from *OpenJarvis* (`orchestrator.py`) or *LangGraph*. | **Build**. Create a lightweight custom orchestrator loop in `core/orchestrator/` avoiding heavy framework lock-in. | High |
| **Tool Registry** | Scattered Langchain tools and `desktop_action_manager`. | 5 | **Yes**. | Borrow the *interface design* from *OpenJarvis* (`tools/`). | **Build**. Standardize a custom Tool interface to ensure all tools map perfectly to JARVIS's UI events. | High |
| **Browser Automation** | None natively integrated (relies on basic link opening). | 2 | No. Too complex to maintain. | Borrow from *browser-use* or *Playwright*. | **Borrow**. Evaluate *browser-use* (Langchain native) as it's currently the industry standard for AI browser control. | Low |
| **Voice Pipeline (STT/TTS/Wake)** | `edge-tts`, `openwakeword`, Groq Whisper. | 9 | **Yes**. Already built perfectly. | No need. | **Keep**. The current pipeline is highly optimized and free. Do not touch. | None |
| **Desktop Automation** | `desktop_action_manager.py` (UI simulated clicks). | 7 | **Yes**. Deeply tied to Windows/Lenovo. | Borrow *OpenInterpreter* or *OS-Copilot* concepts. | **Improve**. Keep current execution but wrap it in the new Tool Registry. | Low |
| **Knowledge Management** | Simple text splitters to FAISS. | 5 | **Yes**. | Borrow *Khoj* or *AnythingLLM* ideas. | **Improve**. Add better markdown parsing and metadata tagging for workspaces. | Medium |
| **Scheduling & Automations** | Basic `daily_brief_manager`. No true CRON. | 3 | **Yes**. | Borrow python `schedule` or *APScheduler*. | **Build**. Implement a lightweight `automations/` background thread loop. | Medium |
| **Local AI Execution** | None (100% Cloud/Groq dependent). | 0 | No. | Borrow from *Ollama* or *LM Studio*. | **Borrow**. Ensure the new Provider Abstraction fully supports an Ollama provider. | Low |
| **Provider Abstraction** | Hardcoded `langchain-groq`. | 2 | **Yes**. | Borrow interface from *LiteLLM* or *OpenJarvis* (`engine/`). | **Build**. Create `providers/base_provider.py` and `groq_provider.py`. Keep it native without adding LiteLLM dependency bloat. | High |
