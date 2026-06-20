# JARVIS Vision

## Current JARVIS
Currently, J.A.R.V.I.S operates as a reactive AI Assistant. 
- It waits for voice or text input.
- It uses a router to decide between real-time search, vision, general conversation, or basic tasks.
- It provides a unified SSE stream response with high quality TTS.
- It acts locally and retains context via a simple vector store.

## Future JARVIS
The goal is to evolve J.A.R.V.I.S from a reactive AI Assistant into a proactive AI Operating System (A-OS).
- **Proactive & Autonomous**: It will have background event loops capable of performing tasks without explicit prompting (e.g., summarizing news, running server health checks).
- **Deep Personalization**: It will maintain a robust identity graph of the user, adapting its tone, actions, and constraints dynamically based on detailed profiles.
- **Agentic Workflows**: Instead of simple one-shot routing, it will implement cyclic reasoning and multi-agent collaboration (planning, execution, reflection).
- **Device Ecosystem**: It will orchestrate external devices (smart home, mobile integrations, servers), treating them as peripheral limbs of the core brain.
- **True Desktop Control**: It will transcend simple URL opening and perform complete browser/DOM and OS-level automation securely.

## Future Architecture Roadmap
* **Kernel**: The core FastAPI asynchronous engine.
* **Memory Subsystem**: Graph Database + Vector FAISS hybrid for complex relational context.
* **Cognitive Subsystem**: ReAct based Agent network instead of simple LLM endpoints.
* **Peripheral Subsystem**: Device integration layer.
