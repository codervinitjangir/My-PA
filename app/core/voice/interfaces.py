"""
app/core/voice/interfaces.py — Abstract Component Interfaces for JARVIS Modular Voice Architecture
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any, Optional, List, Callable
from pydantic import BaseModel, Field

class IntentPrediction(BaseModel):
    intent_type: str = Field(description="Action intent type (e.g. open_app, volume_set, search, chat)")
    action: str = Field(default="", description="Specific action name")
    target: str = Field(default="", description="Target application, website, or payload")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    confidence: float = Field(default=0.0, description="Confidence score between 0.0 and 1.0")

class STTEngine(ABC):
    """Abstract interface for Speech-to-Text engines."""
    
    @abstractmethod
    async def transcribe_chunk(self, audio_chunk: bytes) -> Optional[str]:
        """Process streaming audio chunk and return partial transcript text if ready."""
        pass

    @abstractmethod
    async def transcribe_final(self, full_audio_bytes: bytes) -> Dict[str, Any]:
        """Process complete audio audio and return final transcript dict."""
        pass

class IntentEngine(ABC):
    """Abstract interface for Intent Classification engines."""
    
    @abstractmethod
    async def classify_intent(self, text: str, context: Optional[Dict[str, Any]] = None) -> IntentPrediction:
        """Classify transcript or early tokens into a structured IntentPrediction."""
        pass

class ActionPlanner(ABC):
    """Abstract interface for Action Dispatchers."""
    
    @abstractmethod
    async def execute_action(self, prediction: IntentPrediction) -> Dict[str, Any]:
        """Execute action if confidence >= threshold and return execution result."""
        pass

class LLMEngine(ABC):
    """Abstract interface for LLM response generation."""
    
    @abstractmethod
    def stream_response(
        self,
        prompt: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """Stream text tokens for the given prompt."""
        pass

class TTSEngine(ABC):
    """Abstract interface for Text-to-Speech synthesis engines."""
    
    @abstractmethod
    def synthesize_sentence(self, sentence_text: str, voice: Optional[str] = None) -> AsyncIterator[bytes]:
        """Synthesize sentence string into streaming audio PCM bytes."""
        pass

class AudioOutput(ABC):
    """Abstract interface for audio playback handling."""
    
    @abstractmethod
    def play_chunk(self, pcm_data: bytes) -> None:
        """Play PCM audio chunk."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Interrupt and stop playback immediately (for barge-in)."""
        pass

class VoicePipeline(ABC):
    """Abstract interface for full voice interaction pipeline."""
    
    @abstractmethod
    async def process_voice_session(self, websocket: Any) -> None:
        """Manage bi-directional voice WebSocket interaction session."""
        pass
