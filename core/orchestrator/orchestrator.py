import logging
from typing import Optional, Iterator, Union, Dict, Any
from adapters.legacy_chat_adapter import LegacyChatAdapter
from core.memory.memory_manager import MemoryManager

logger = logging.getLogger("J.A.R.V.I.S")

class Orchestrator:
    """
    The main routing hub for the OS. 
    Receives raw inputs, enriches them with Context and Memory, 
    then delegates to the Decision Engine or Legacy Adapters.
    """
    def __init__(
        self, 
        chat_adapter: LegacyChatAdapter, 
        memory_manager: MemoryManager,
        context_manager=None, # To be implemented in P3
        decision_engine=None  # To be implemented in P2
    ):
        self.chat_adapter = chat_adapter
        self.memory_manager = memory_manager
        self.context_manager = context_manager
        self.decision_engine = decision_engine

    def handle_command_stream(self, session_id: str, query: str, imgbase64: Optional[str] = None) -> Iterator[Union[str, Dict[str, Any]]]:
        """
        The main pipeline:
        Voice/Text -> Context -> Memory -> [DecisionEngine] -> Tools -> Response
        """
        logger.info(f"[Orchestrator] Processing command: {query[:50]}...")

        enriched_query = query
        
        # 1. Context Injection (P3)
        if self.context_manager:
            context_data = self.context_manager.get_current_context()
            enriched_query = f"[Context: {context_data}]\n{enriched_query}"

        # 2. Memory Injection (P1)
        if self.memory_manager:
            enriched_query = self.memory_manager.inject_context(session_id, enriched_query)

        # 3. Decision Engine (P2)
        if self.decision_engine:
            decision = self.decision_engine.evaluate(enriched_query)
            if decision == "SILENT":
                yield {"_activity": {"event": "silent_execution"}}
                # Execute silently, don't yield text
                return

        # 4. Fallback to Legacy Chat Adapter for execution and response
        yield from self.chat_adapter.process_query_stream(session_id, enriched_query, imgbase64)
