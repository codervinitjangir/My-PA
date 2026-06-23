import logging
from core.orchestrator.orchestrator import Orchestrator

logger = logging.getLogger("J.A.R.V.I.S")

class VoiceStateMachine:
    """
    Manages the deterministic state transitions for Voice interactions.
    States: SLEEP, WAKE, LISTENING, UNDERSTANDING, THINKING, EXECUTING, RESPONDING, FOLLOW_UP, SILENT
    """
    def __init__(self, orchestrator: Orchestrator):
        self.state = "SLEEP"
        self.orchestrator = orchestrator

    def transition_to(self, new_state: str):
        logger.info(f"[StateMachine] Transitioning from {self.state} to {new_state}")
        self.state = new_state
        
        if self.state == "UNDERSTANDING":
            self.handle_understanding()

    def handle_understanding(self):
        """
        Placeholder logic to pull in context, STT transcript, and route to Orchestrator.
        """
        logger.info("[StateMachine] Handling UNDERSTANDING -> passing to Orchestrator (THINKING)")
        self.transition_to("THINKING")
        
        # Fake payload for V1 test
        payload = "Test Command"
        # The orchestrator handles THINKING -> EXECUTING -> RESPONDING
        for response in self.orchestrator.handle_command_stream("voice_session", payload):
            # Process response...
            pass
            
        self.transition_to("FOLLOW_UP")
