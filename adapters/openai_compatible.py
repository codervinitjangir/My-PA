"""Language model access over the OpenAI chat completions API.

Groq, OpenAI, Together, Fireworks, Ollama, and llama.cpp all expose this same
interface, so one implementation covers every provider Bruno is likely to want,
including running entirely offline later. Switching between them is a base URL
and a model name rather than new code, which is the whole reason this file is
generic and :mod:`bruno.llm.groq` is four lines.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Generator, Iterator, Sequence
from typing import Any, Final

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
)

from core.protocols import (
    LLMAuthError,
    LLMConnectionError,
    LLMError,
    LLMQuotaError,
    LLMRateLimitError,
    LLMToolCallError,
    Message,
    ToolCall,
    Toolbox,
)
from adapters.thinking import strip_thinking

logger = logging.getLogger(__name__)

# Long enough to survive a slow first token, short enough that a dead network
# does not leave the user staring at nothing. Bruno has no way to show progress.
DEFAULT_TIMEOUT_SECONDS: Final = 20.0

# Replies are spoken aloud, so length is a latency cost rather than a style
# choice. This is a backstop for a model that ignores the prompt; it is not
# the mechanism for keeping answers short.
DEFAULT_MAX_TOKENS: Final = 400

# Deliberately low. Someone is waiting to be answered, and would rather hear
# that something is wrong than sit through a long retry ladder in silence.
DEFAULT_MAX_RETRIES: Final = 1

# How many times the model may call tools before it has to answer with words.
# Two is enough for "look at the screen, then check something else"; more than
# that and a model stuck in a loop would keep a user waiting indefinitely for a
# reply that never comes.
DEFAULT_MAX_TOOL_ROUNDS: Final = 3

# Phrases a service uses when the model emitted a tool call it will not accept.
# Matched as text because these arrive as generic errors with no code to test,
# and the wording differs per service and per failure: one is a model that
# wrote invalid JSON, another is a model that fused the tool's name and its
# arguments into a single string. All are recoverable by asking again without
# tools, so they are treated alike.
_TOOL_FAILURE_MARKERS: Final = (
    "failed to call a function",
    "tool call validation failed",
    "which was not in request.tools",
    "thought_signature",
)

# Phrases distinguishing a daily allowance from a per-minute one. Groq names
# the window in the message and nowhere else.
_DAILY_QUOTA_MARKERS: Final = ("per day", "(tpd)", "(rpd)")


# Sent alongside an image returned by a tool. The chat API only accepts text
# in a tool message, so pictures have to arrive as a following user turn; this
# is the sentence that carries them.
#
# It also restates brevity, because handing a model a picture reliably makes it
# describe everything in the picture. Left alone it answered "what's this?" in
# two hundred and thirteen words -- a minute and a half of speech for a
# two-word question. The system prompt says all of this already; an image is
# simply strong enough to override it.
IMAGE_NOTE: Final = (
    "Here is what I captured. Answer what they actually asked, in a sentence "
    "or two, out loud, the way you normally talk. Do not narrate everything "
    "on the screen and do not list what you can see -- only mention the parts "
    "that answer the question."
)


def _message_payload(message: Message) -> dict[str, Any]:
    """Convert one message into the wire format.

    Four shapes exist, and only the first is what most of Bruno ever produces:
    plain text, an assistant turn requesting tools, a tool's answer, and a
    user turn carrying images.
    """
    if message.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id,
            "content": message.content,
        }

    if message.tool_calls:
        return {
            "role": "assistant",
            # Null rather than empty: a model that called a tool without
            # speaking first has no content, and some endpoints reject "".
            "content": message.content or None,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in message.tool_calls
            ],
        }

    if message.images:
        parts: list[dict[str, Any]] = []
        if message.content:
            parts.append({"type": "text", "text": message.content})
        parts += [
            {"type": "image_url", "image_url": {"url": uri}} for uri in message.images
        ]
        return {"role": message.role, "content": parts}

    return {"role": message.role, "content": message.content}


# Substituted for a screenshot when the answering service has no eyes. Written
# as an instruction rather than an apology, because the model has to turn it
# into something Bruno would actually say.
BLIND_NOTE: Final = (
    "(A screenshot was taken, but you cannot see images right now: the "
    "services that can see have run out of free usage for today. Tell them "
    "you can't see their screen at the moment, in your own words and in one "
    "short sentence, then help however you can without it.)"
)


def _describe_missing_images(payload: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace image content with an explanation the model can act on.

    Returns a new list; the caller's payload is left alone, since the same
    messages may be sent to a different service that *can* see them.
    """
    cleaned: list[dict[str, Any]] = []
    for message in payload:
        content = message.get("content")
        if not isinstance(content, list):
            cleaned.append(message)
            continue

        parts = [part.get("text", "") for part in content if part.get("type") == "text"]
        if any(part.get("type") == "image_url" for part in content):
            parts.append(BLIND_NOTE)
        cleaned.append({**message, "content": " ".join(filter(None, parts))})
    return cleaned


def _has_images(payload: Sequence[dict[str, Any]]) -> bool:
    """Whether any message carries a picture.

    Text-only messages hold a plain string, so only the list form -- the one
    built by :func:`_message_payload` for images -- needs inspecting.
    """
    return any(
        isinstance(message.get("content"), list)
        and any(part.get("type") == "image_url" for part in message["content"])
        for message in payload
    )


def _tool_exchange(
    tools: Toolbox,
    calls: Sequence[ToolCall],
    spoken: str,
    *,
    as_text: bool = False,
) -> list[dict[str, Any]]:
    """Run the requested tools and build the messages recording what happened.

    Args:
        tools: What to run the calls against.
        calls: What the model asked for.
        spoken: Anything it said before asking.
        as_text: Report results as ordinary conversation instead of as formal
            tool messages. See :func:`_tool_exchange_as_text`.

    Returns:
        The assistant turn that asked, one turn per tool answer, and -- if any
        tool produced pictures -- a final user turn carrying them.
    """
    results = [(call, tools.run(call)) for call in calls]
    images = [uri for _call, result in results for uri in result.images]

    if as_text:
        return _tool_exchange_as_text(results, spoken, images)

    exchange = [_message_payload(Message("assistant", spoken, tool_calls=tuple(calls)))]
    for call, result in results:
        exchange.append(
            _message_payload(Message("tool", result.content, tool_call_id=call.id))
        )

    if images:
        exchange.append(
            _message_payload(Message("user", IMAGE_NOTE, images=tuple(images)))
        )
    return exchange


def _tool_exchange_as_text(
    results: Sequence[tuple[ToolCall, Any]], spoken: str, images: Sequence[str]
) -> list[dict[str, Any]]:
    """Describe a tool exchange as plain conversation.

    Some services will not accept their own tool call played back to them
    through this API. Gemini rejects the follow-up request outright, saying the
    function call is "missing a thought_signature" -- a field its native
    protocol carries and the OpenAI-compatible layer does not. The tool has
    already run by then, so the visible result is a browser that opens and an
    Bruno that never says anything.

    Reporting the same information as ordinary text sidesteps the formal
    protocol entirely. It costs a little precision and works everywhere.
    """
    reported = " ".join(
        f"I used {call.name} and it returned: {result.content}" for call, result in results
    )
    exchange: list[dict[str, Any]] = []
    if spoken:
        exchange.append({"role": "assistant", "content": spoken})

    note = f"{reported} {IMAGE_NOTE}" if images else f"{reported} Now answer them."
    exchange.append(
        _message_payload(Message("user", note, images=tuple(images)))
    )
    return exchange


def _classify(exc: OpenAIError, label: str) -> LLMError:
    """Translate an SDK exception into an error Bruno can speak about."""
    # Raised mid-stream, as a bare APIError rather than a status error, when
    # the model emits a tool call the service will not accept. Checked first
    # because it is the one failure here that is worth retrying.
    message = str(exc).lower()
    if any(marker in message for marker in _TOOL_FAILURE_MARKERS):
        return LLMToolCallError(f"{label} rejected the model's tool call: {exc}")

    if isinstance(exc, (AuthenticationError, PermissionDeniedError)):
        return LLMAuthError(f"{label} rejected the API key: {exc}")
    if isinstance(exc, RateLimitError):
        message = str(exc).lower()
        if any(marker in message for marker in _DAILY_QUOTA_MARKERS):
            return LLMQuotaError(f"{label} daily quota exhausted: {exc}")
        return LLMRateLimitError(f"{label} rate limited the request: {exc}")
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return LLMConnectionError(f"Could not reach {label}: {exc}")
    if isinstance(exc, APIStatusError) and exc.status_code >= 500:
        # The service is broken rather than the request, so this reads to a
        # user the same way an outage does.
        return LLMConnectionError(f"{label} is having problems: {exc}")
    return LLMError(f"{label} request failed: {exc}")


class OpenAICompatibleProvider:
    """Streams replies from any OpenAI-compatible endpoint.

    Satisfies :class:`~bruno.core.protocols.LLMProvider`.

    Args:
        api_key: Credential for the service.
        model: Model identifier as the provider names it.
        base_url: API root. ``None`` uses OpenAI itself.
        label: Provider name for logs.
        temperature: Sampling temperature. Slightly above zero keeps Bruno from
            answering the same question in identical words every time, which
            reads as robotic in speech.
        max_tokens: Hard ceiling on reply length.
        timeout: Seconds to wait for the request.
        max_retries: Automatic retries for transient failures.
        max_tool_rounds: How many times the model may call tools before it is
            required to answer in words.
        vision_model: Model used for requests carrying images. Blank uses
            ``model`` for everything. Splitting them lets the conversation run
            on the best talker available while pictures go to whichever model
            can see, and costs no extra round trip -- a turn that looks at the
            screen already makes two requests.
        vision_reasoning_effort: Sent with vision requests only, and only when
            set. Vision models are often reasoning models, which spend hundreds
            of tokens deliberating before answering; on a spoken reply that is
            silence the user sits through. Provider-specific and opt-in, since
            an endpoint that does not know the parameter rejects the request.
        tool_results_as_text: Report tool results as ordinary conversation
            rather than as formal tool messages. Needed by services that will
            not accept their own tool call played back through this API; see
            :func:`_tool_exchange_as_text`.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
        label: str = "openai",
        temperature: float = 0.7,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS,
        vision_model: str = "",
        vision_reasoning_effort: str = "",
        tool_results_as_text: bool = False,
    ) -> None:
        if not api_key:
            raise LLMError(
                f"No API key for {label}. Add it to .env and restart."
            )

        self._label = label
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._max_tool_rounds = max_tool_rounds
        # Left empty when the service cannot see, rather than defaulted to the
        # text model: the difference is what lets a screenshot be handled
        # gracefully instead of sent to a model that will reject it.
        self._vision_model = vision_model
        self._vision_reasoning_effort = vision_reasoning_effort
        self._tool_results_as_text = tool_results_as_text
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            # Transient 429s and 5xxs are retried by the SDK with backoff.
            # Kept low: a user waiting to be answered would rather hear that
            # something is wrong than sit through a long retry ladder.
            max_retries=max_retries,
        )

    @property
    def can_see(self) -> bool:
        """Whether this service can be shown a screenshot."""
        return bool(self._vision_model)

    @property
    def name(self) -> str:
        """Provider and model, for logs and diagnostics."""
        if self._vision_model and self._vision_model != self._model:
            return f"{self._label}/{self._model} (+{self._vision_model} for images)"
        return f"{self._label}/{self._model}"

    def stream_reply(
        self, messages: Sequence[Message], tools: Toolbox | None = None
    ) -> Iterator[str]:
        """Generate a reply, yielding fragments as they arrive.

        When ``tools`` is supplied the model may ask to run one before
        answering. That costs an extra round trip, but only on the turns that
        use it: declaring tools does not slow down an ordinary reply, because
        a model that does not call one simply streams its answer as usual.

        Any chain-of-thought is stripped before the text is returned. See
        :mod:`bruno.llm.thinking` for why that belongs here and not in the caller.

        Args:
            messages: Conversation so far, system prompt first.
            tools: Capabilities the model may invoke, or ``None`` for none.

        Yields:
            Text fragments in order.

        Raises:
            LLMError: If the request fails or the stream breaks partway.
        """
        return strip_thinking(self._generate(messages, tools))

    def _generate(
        self, messages: Sequence[Message], tools: Toolbox | None
    ) -> Iterator[str]:
        """Run the request-and-tool loop, yielding raw model output."""
        payload = [_message_payload(message) for message in messages]
        specs = tools.specs() if tools is not None else []

        for round_number in range(self._max_tool_rounds + 1):
            # The final pass offers no tools, so a model that would otherwise
            # keep calling them has to produce words. Without this a confused
            # model can leave the user waiting on a reply that never comes.
            offering = specs if specs and round_number < self._max_tool_rounds else None

            try:
                calls, spoken = yield from self._stream_once(payload, offering)
            except LLMToolCallError:
                if not offering:
                    raise
                # The model wrote a tool call the service would not accept.
                # Asking the same question with no tools almost always works,
                # and an answer without the tool beats saying nothing at all --
                # which is what the user otherwise gets, repeatedly, since the
                # next question fails the same way.
                logger.warning("Invalid tool call; retrying without tools")
                calls, spoken = yield from self._stream_once(payload, None)

            if not calls or tools is None:
                return

            logger.info(
                "Round %d: model asked for %s",
                round_number + 1,
                ", ".join(call.name for call in calls),
            )
            payload.extend(
                _tool_exchange(tools, calls, spoken, as_text=self._tool_results_as_text)
            )

    def _stream_once(
        self, payload: list[dict[str, Any]], tool_specs: list[dict] | None
    ) -> Generator[str, None, tuple[tuple[ToolCall, ...], str]]:
        """Stream one completion.

        Yields:
            Text fragments as they arrive.

        Returns:
            A ``(tool_calls, text)`` pair. Text is returned as well as yielded
            because it has to go back into the history if a tool follows it.
        """
        # The model is chosen by what is being sent rather than configured per
        # call: a request carrying a screenshot needs a model that can see, and
        # every other request is better served by the best talker available.
        seeing = _has_images(payload)

        if seeing and not self.can_see:
            # This service cannot be shown a picture, and sending one anyway
            # gets the whole request rejected. Replacing the image with an
            # explanation lets the turn finish: Bruno says it cannot see right
            # now and carries on talking, which is what a person would do.
            logger.info("%s cannot see images; answering without the screenshot", self._label)
            payload = _describe_missing_images(payload)
            seeing = False

        model = self._vision_model if seeing else self._model

        request: dict[str, Any] = {
            "model": model,
            "messages": payload,
            "stream": True,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        # Tools are withheld from a request that already carries a picture.
        # Offered them, the model reliably takes another screenshot instead of
        # describing the one it was just handed -- three captures and three
        # uploads for one question, which is both slow and the quickest way to
        # exhaust a rate limit. A request holding an image has everything it
        # needs; its job is to answer.
        if tool_specs and not seeing:
            request["tools"] = tool_specs
            request["tool_choice"] = "auto"
        if seeing and self._vision_reasoning_effort:
            # Passed through the body rather than as a named argument, because
            # the values a provider accepts here are its own and do not match
            # the SDK's idea of them.
            request["extra_body"] = {"reasoning_effort": self._vision_reasoning_effort}

        # Tool calls arrive split across chunks exactly as text does: a name in
        # one, arguments a few characters at a time in the next. They are
        # reassembled by index, which is the only field present on every piece.
        partial: dict[int, dict[str, str]] = {}
        spoken: list[str] = []

        try:
            stream = self._client.chat.completions.create(**request)
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                fragment = delta.content
                if fragment:
                    spoken.append(fragment)
                    yield fragment

                for piece in getattr(delta, "tool_calls", None) or ():
                    slot = partial.setdefault(
                        piece.index, {"id": "", "name": "", "arguments": ""}
                    )
                    if piece.id:
                        slot["id"] = piece.id
                    function = getattr(piece, "function", None)
                    if function is not None:
                        if function.name:
                            slot["name"] = function.name
                        if function.arguments:
                            slot["arguments"] += function.arguments
        except OpenAIError as exc:
            error = _classify(exc, self.name)
            if isinstance(error, LLMToolCallError) and spoken:
                # Part of the reply is already on its way to the speaker, so a
                # retry would say it twice. Downgrade to a plain failure.
                raise LLMError(str(error)) from exc
            raise error from exc
        except (OSError, ValueError) as exc:
            # A connection dropped mid-stream surfaces from the underlying
            # transport rather than as an SDK error, so it would otherwise
            # escape as an unhandled exception and kill the worker thread.
            raise LLMConnectionError(f"{self.name} stream broke: {exc}") from exc

        calls = tuple(
            ToolCall(id=slot["id"], name=slot["name"], arguments=slot["arguments"] or "{}")
            for _, slot in sorted(partial.items())
            if slot["name"]
        )
        return calls, "".join(spoken)

    def warm_up(self) -> bool:
        """Open the HTTPS connection before the user needs it.

        Measured against Groq, the first request costs roughly 1100 ms to first
        token and later ones 170-450 ms. The difference is DNS, the TLS
        handshake, and connection setup, not the model. Paying it at startup
        moves that second of silence off the user's first sentence, which is
        the one that decides whether Bruno feels responsive.

        Lists models rather than generating: it primes the same connection
        pool without spending tokens.

        Returns:
            True if the connection was established. Failure is not fatal --
            the first real request simply pays the cost instead.
        """
        started = time.perf_counter()
        try:
            listing = self._client.models.list()
        except OpenAIError as exc:
            logger.debug("Connection warm-up failed: %s", exc)
            return False

        logger.info(
            "%s connection warmed in %.0f ms", self.name, (time.perf_counter() - started) * 1000
        )

        # Providers retire models regularly, and the resulting failure names a
        # model without saying it is gone -- which reads as Bruno being broken
        # rather than as one line of configuration being out of date. The
        # listing is already in hand, so saying so costs nothing.
        try:
            available = {model.id for model in listing.data}
        except (AttributeError, TypeError):
            return True

        # Some services list models with a namespace the request does not use
        # -- Gemini answers to "gemini-3.6-flash" but lists it as
        # "models/gemini-3.6-flash" -- so compare the last segment too, or the
        # warning fires on a model that works perfectly.
        available |= {name.rsplit("/", 1)[-1] for name in available}

        if available and self._model.rsplit("/", 1)[-1] not in available:
            logger.warning(
                "%s does not list model %r. Set BRUNO_LLM_MODEL to one of: %s",
                self._label,
                self._model,
                ", ".join(sorted(available)[:8]),
            )
        return True

    def available_models(self) -> list[str]:
        """List model identifiers the endpoint accepts.

        Providers retire models regularly, and the resulting error names a
        model rather than explaining the alternatives. This exists so that
        diagnostics can show what is currently valid.

        Raises:
            LLMError: If the listing request fails.
        """
        try:
            return sorted(model.id for model in self._client.models.list().data)
        except OpenAIError as exc:
            raise _classify(exc, self.name) from exc
