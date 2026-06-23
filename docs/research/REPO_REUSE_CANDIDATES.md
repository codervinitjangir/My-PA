# Repository Reuse Candidates

The following table evaluates components from **OpenJarvis** (and other potential open-source projects) for reuse within the JARVIS architecture.

| Component | Source Repository | Benefit | Effort | Risk | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Provider Abstraction** | OpenJarvis (`engine/`) | Unifies LLM calls (Groq, Ollama, OpenAI) preventing vendor lock-in. | Medium | Low | **Adapt Partially**. Use the interface design, but write our own lightweight implementation specifically designed around our new `providers/` structure. |
| **Tool Registry** | OpenJarvis (`tools/`) | Highly modular, atomic tools that are easily discoverable by agents. | High | Medium | **Adapt Partially**. Borrow the dynamic registration pattern, but keep our existing working implementations for desktop control. |
| **Deep Research Agent** | OpenJarvis (`agents/deep_research.py`) | Provides a powerful, recursive web-scraping and synthesis loop. | Medium | Low | **Reuse as-is (with tweaks)**. Add as a specialized agent inside `agents/research_agent/`. |
| **Browser Automation** | OpenJarvis (`tools/browser.py`) | Playwright-based headless browsing with accessibility tree parsing. | High | Medium | **Ignore** for now. Playwright is heavy. If JARVIS needs UI automation, consider borrowing from `browser-use` instead. |
| **MCP Adapter** | OpenJarvis (`tools/mcp_adapter.py`) | Instantly unlocks hundreds of community tools via Model Context Protocol. | Low | Low | **Rewrite completely**. It's better to implement a native, lightweight MCP client integrated directly into our new `tools/` layer. |
| **Digital Observer** | Current JARVIS (`observers/`) | Extremely fast, tailored screen/window context gathering. | - | Low | **Keep Current**. OpenJarvis lacks this deep OS integration. |
| **Vector Memory** | Current JARVIS (`vector_store.py`) | Lightweight, zero-configuration FAISS setup. | - | Low | **Keep Current**, but expand the folder structure to support Profiles. |
| **Agent Orchestrator** | OpenJarvis (`agents/orchestrator.py`) | True delegation and sub-tasking rather than simple routing. | High | High | **Adapt Partially**. Move away from `BrainService` routing slowly, adopting a simplified version of this orchestrator. |
