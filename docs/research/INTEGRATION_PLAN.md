# JARVIS Integration & Refactoring Plan

## Phase 1: Immediate Improvements (Cleanup & Standardization)
*Focus: Paying down critical technical debt without breaking existing functionality.*

1. **Duplicate Cleanup**: Review and eliminate dead code in the `/archive/` folder.
2. **Refactor `app/main.py`**: Extract the complex TTS streaming logic (`_stream_generator`, `_split_sentences`) into a dedicated `app/utils/stream_utils.py`.
3. **Merge Groq Services**: Combine `GroqService` and `RealtimeGroqService` into a unified implementation, where search capabilities are simply passed as dynamic tools rather than requiring a separate service class.
   - **Priority**: High
   - **Complexity**: Low
   - **Files Impacted**: `app/services/groq_service.py`, `app/services/realtime_service.py`, `app/main.py`.

## Phase 2: Core Architecture Improvements (Provider & Tool Layers)
*Focus: Creating the foundation for scalability.*

1. **Implement Provider Abstraction**:
   - Create `providers/base_provider.py` defining standard methods (`generate`, `stream`, `analyze_vision`).
   - Create `providers/groq_provider.py` (migrating existing working code).
   - Create `providers/provider_manager.py` to handle instantiation.
   - *Rule*: Backward compatibility is mandatory; the rest of the app should continue working seamlessly.
2. **Implement Unified Tool Registry**:
   - Create `tools/registry.py` inspired by OpenJarvis.
   - Migrate `desktop_action_manager` capabilities and LangChain search tools into isolated, atomic tool files (e.g., `tools/browser_tool.py`, `tools/search_tool.py`).
   - **Priority**: High
   - **Complexity**: Medium
   - **Files Impacted**: `jarvis_os/desktop_action/`, `app/services/`, new `providers/` and `tools/` directories.

## Phase 3: Intelligence Layer (Agents & Orchestration)
*Focus: Upgrading from a simple router to a multi-agent system.*

1. **Create Agent Orchestrator**:
   - Replace the static `BrainService` routing logic with a true orchestrator (`core/orchestrator/`).
   - Create specialized agents: `agents/coding_agent.py`, `agents/research_agent.py`, `agents/general_agent.py`.
2. **Integrate OpenJarvis Patterns**:
   - Adapt OpenJarvis's `deep_research.py` pattern for complex queries.
   - **Priority**: Medium
   - **Complexity**: High
   - **Files Impacted**: `app/services/brain_service.py`, `jarvis_os/core/request_router.py`.

## Phase 4: Automation Layer
*Focus: Expanding JARVIS's ability to operate the computer.*

1. **Enhance Browser Automation**:
   - Evaluate Playwright vs current implementation. Borrow OpenJarvis's `browser_axtree.py` concepts for better DOM understanding if needed.
2. **Model Context Protocol (MCP)**:
   - Implement an MCP client tool, allowing JARVIS to immediately gain access to thousands of open-source MCP servers (GitHub, Slack, Google Drive).
   - **Priority**: Medium
   - **Complexity**: Medium
   - **Files Impacted**: `tools/mcp_client.py`.

## Phase 5: Long-term Learning Systems
*Focus: Continuous improvement and deep personalization.*

1. **Memory System Overhaul**:
   - Restructure `app/services/vector_store.py` into a robust `memory/` module.
   - Add partitions for `user-profile/`, `projects/`, and `vector-store/`.
2. **Self-Correction Loops**:
   - Implement reflection patterns where JARVIS evaluates its own task success and updates its memory to avoid repeating mistakes.
   - **Priority**: Low
   - **Complexity**: High
   - **Files Impacted**: `memory/`, `core/orchestrator/`.
