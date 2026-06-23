import logging
from typing import Iterator, Union, Dict, Any, Optional

logger = logging.getLogger("J.A.R.V.I.S")

class LegacyChatAdapter:
    """
    Adapter pattern to wrap the existing monolithic ChatService.
    Ensures the new OS components can use the chat logic without
    being tightly coupled to it. Preserves all working functionality.
    """
    def __init__(self, chat_service):
        self.chat_service = chat_service

    def process_query_stream(self, session_id: str, message: str, imgbase64: Optional[str] = None) -> Iterator[Union[str, Dict[str, Any]]]:
        """
        Passes the query to the legacy chat service stream.
        """
        try:
            return self.chat_service.process_jarvis_message_stream(session_id, message, imgbase64)
        except Exception as e:
            logger.error(f"[LegacyChatAdapter] Error processing stream: {e}")
            yield {"error": str(e)}
