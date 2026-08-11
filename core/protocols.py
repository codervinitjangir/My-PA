"""Interfaces between Bruno's swappable components.

Each stage of the conversation -- hearing, thinking, speaking -- is defined
here as a structural protocol rather than a base class. Concrete engines do not
import or subclass anything from this module; they simply match the shape. That
keeps the dependency arrow pointing inward: ``bruno.stt`` knows nothing about who
consumes it, and the pipeline knows nothing about faster-whisper.

The practical payoff is that swapping a cloud model for a local one, or Piper
for another synthesiser, means adding a class and changing one line of wiring
rather than editing the pipeline.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from voice.audio.recorder import AudioClip

Role = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A model's request to run one tool.

    Attributes:
        id: Identifier the provider uses to match a result to this request.
        name: Which tool to run.
        arguments: JSON object as a string, exactly as the model wrote it.
            Left unparsed here because a model can and does emit malformed
            JSON, and the tool layer is where that becomes a message the model
            can recover from rather than an exception.
    """

    id: str
    name: str
    arguments: str = "{}"


@dataclass(frozen=True, slots=True)
class ToolResult:
    """What running a tool produced.

    Attributes:
        content: Text handed back to the model.
        images: Data URIs to show the model. Kept separate from ``content``
            because the chat API only accepts strings in a tool message; an
            image has to follow as a user message instead.
    """

    content: str
    images: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Message:
    """One turn of a conversation.

    Attributes:
        role: Who is speaking.
        content: The text.
        tool_calls: Tools an assistant turn asked to run.
        tool_call_id: Which request a ``tool`` turn answers.
        images: Data URIs attached to a user turn.
    """

    role: Role
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str = ""
    images: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Transcript:
    """What Bruno heard.

    Attributes:
        text: The recognised words, stripped of surrounding whitespace.
        language: ISO 639-1 code detected by the engine.
        latency: Seconds spent transcribing, for the latency budget.
    """

    text: str
    language: str
    latency: float

    @property
    def is_empty(self) -> bool:
        """Whether the audio contained no usable speech."""
        return not self.text


@runtime_checkable
class STTEngine(Protocol):
    """Converts recorded audio into text."""

    def load(self) -> None:
        """Prepare the engine for inference.

        Implementations should be idempotent and may block for several
        seconds. Callers are expected to invoke this at startup rather than on
        the first user request.
        """
        ...

    def transcribe(self, clip: AudioClip) -> Transcript:
        """Transcribe one recording.

        Args:
            clip: Audio at the sample rate the engine expects.

        Returns:
            The transcript, which may be empty if the clip held no speech.
        """
        ...


@runtime_checkable
class Toolbox(Protocol):
    """The things Bruno can do besides talk.

    Split from the provider deliberately. The provider knows the wire protocol
    for requesting a tool; it knows nothing about screens or files. Adding a
    capability means adding a tool here, not editing the language model layer.
    """

    def specs(self) -> list[dict]:
        """JSON-schema descriptions of every tool, as the chat API wants them."""
        ...

    def run(self, call: ToolCall) -> ToolResult:
        """Execute one tool call.

        Must not raise. A tool that fails returns a result saying so, because
        the model can apologise for a failed screenshot but cannot recover
        from an exception thrown inside the request loop.
        """
        ...


@runtime_checkable
class LLMProvider(Protocol):
    """Generates Bruno's replies."""

    @property
    def name(self) -> str:
        """Human-readable identifier, for logs and diagnostics."""
        ...

    def stream_reply(
        self, messages: Sequence[Message], tools: Toolbox | None = None
    ) -> Iterator[str]:
        """Generate a reply, yielding text as it is produced.

        Streaming is required rather than optional. Bruno begins speaking its
        first sentence while later ones are still being written, so a provider
        that returned only a finished string would add its entire generation
        time to the pause before Bruno makes a sound.

        Args:
            messages: Conversation so far, oldest first, including the system
                prompt.
            tools: Capabilities the model may invoke. ``None`` disables tool
                use entirely. Declaring tools costs nothing on turns that do
                not use one: the model simply answers and streams as usual.

        Yields:
            Fragments of the reply in order. Fragments are arbitrary chunks,
            not words or sentences; callers needing sentences must assemble
            them.

        Raises:
            LLMError: If generation fails.
        """
        ...


class LLMError(RuntimeError):
    """A language model request failed.

    Subclassed by cause rather than reported as one generic failure, because
    Bruno has to say what went wrong out loud. "I lost my connection" and "my key
    stopped working" call for different responses from the user, and a single
    error type would force both into the same unhelpful sentence.
    """

    spoken = "Sorry, something went wrong reaching my language model."


class LLMConnectionError(LLMError):
    """The service could not be reached, or the request timed out."""

    spoken = "I can't reach the internet right now."


class LLMAuthError(LLMError):
    """The credential was rejected."""

    spoken = "My API key stopped working. You'll need to set a new one."


class LLMRateLimitError(LLMError):
    """Too many requests, or the account's quota is exhausted."""

    spoken = "I'm being rate limited. Give me a moment and try again."


class LLMQuotaError(LLMRateLimitError):
    """The account's allowance for the day is spent.

    Separate from an ordinary rate limit because the advice is different.
    "Give me a moment and try again" is right for a per-minute limit and
    actively misleading for a daily one, where the answer is hours.
    """

    spoken = (
        "I've used up my allowance with Groq for today. "
        "It resets tomorrow, or you can raise the limit in your Groq console."
    )


class LLMToolCallError(LLMError):
    """The model produced a tool call the service could not accept.

    Recoverable, and treated as such: the same question asked without tools
    almost always succeeds, so this should be retried rather than spoken. It
    reaches the user only if answering without tools fails too.
    """

    spoken = "Something went wrong while I was trying to do that."


@runtime_checkable
class TTSEngine(Protocol):
    """Speaks Bruno's replies aloud."""

    @property
    def name(self) -> str:
        """Human-readable identifier, for logs and diagnostics."""
        ...

    def start(self) -> None:
        """Prepare the engine and open the output device."""
        ...

    def stop(self) -> None:
        """Release the output device and any subprocess."""
        ...

    def speak_stream(self, fragments: Iterable[str]) -> None:
        """Speak text arriving as a stream, blocking until playback ends.

        Takes a stream rather than a string for the same reason
        :meth:`LLMProvider.stream_reply` yields one: the opening sentence is
        spoken while the rest of the reply is still being generated.

        Args:
            fragments: Text chunks in order.
        """
        ...

    def stream_sentences(self, fragments: Iterable[str]) -> Iterator[str]:
        """Speak a fragment stream, yielding each sentence as it is queued.

        Returns once the final sentence has been handed to the synthesiser,
        not once it has been heard; pair with :meth:`wait_until_spoken`.

        Args:
            fragments: Text chunks in order.

        Yields:
            Each sentence sent for synthesis.
        """
        ...

    def wait_until_spoken(self) -> bool:
        """Block until synthesis and playback have both finished."""
        ...

    def interrupt(self) -> None:
        """Stop speaking as soon as possible, discarding queued audio."""
        ...
