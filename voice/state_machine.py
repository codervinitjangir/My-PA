import logging
import queue
import threading
from core.orchestrator.orchestrator import Orchestrator
from core.state import StateMachine, State

# Bruno imports
from voice.pipeline import Pipeline
from adapters.factory import load_providers
from adapters.conversation import Conversation
from adapters.chain import ProviderChain
from voice.tts.piper import PiperVoice
from voice.stt.whisper import WhisperEngine
from voice.audio.recorder import AudioRecorder
from voice.hands_free import HandsFreeMode
from tools.registry import Toolbox
from tools.browser import open_tool, control_tool
from tools.screen import screen_tool

logger = logging.getLogger("J.A.R.V.I.S")

class VoiceStateMachine:
    """
    Manages the deterministic state transitions for Voice interactions.
    Now wraps the advanced Bruno Pipeline for zero-latency TTS/STT and LLM fallback.
    """
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.bruno_state = StateMachine()
        self.pipeline = None
        self.hands_free = None
        self._setup_bruno_pipeline()

    def _setup_bruno_pipeline(self):
        try:
            # Initialize robust LLM chain (Groq -> Gemini -> Cerebras)
            providers = load_providers()
            chain = ProviderChain(providers)
            
            # Setup Tools
            toolbox = Toolbox()
            toolbox.register(open_tool())
            toolbox.register(control_tool())
            toolbox.register(screen_tool())

            # Audio components
            voice = PiperVoice()
            transcriber = WhisperEngine()
            recorder = AudioRecorder(always_on=True)
            conversation = Conversation(
                system_prompt="You are Jarvis, a helpful and concise AI assistant."
            )

            # Create the zero-latency pipeline
            self.pipeline = Pipeline(
                recorder=recorder,
                transcriber=transcriber,
                provider=chain,
                voice=voice,
                conversation=conversation,
                state=self.bruno_state,
                tools=toolbox,
            )
            
            # Initialize hands-free VAD mode
            self.hands_free = HandsFreeMode(
                recorder=recorder,
                pipeline=self.pipeline,
                state=self.bruno_state
            )
            
            logger.info("[VoiceStateMachine] Bruno voice pipeline successfully integrated.")
        except Exception as e:
            logger.error(f"[VoiceStateMachine] Failed to initialize Bruno pipeline: {e}")

    def start(self):
        """Starts the voice pipeline and audio devices."""
        if self.pipeline:
            self.pipeline.start()
            self.hands_free.prepare()

    def stop(self):
        """Stops the voice pipeline."""
        if self.pipeline:
            self.pipeline.stop()
        if self.hands_free:
            self.hands_free.close()

    def transition_to(self, new_state: str):
        # Map legacy Jarvis states to Bruno states if needed
        logger.info(f"[StateMachine] Transitioning to {new_state}")

