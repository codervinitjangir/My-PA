"""Declaring tools to the model and running the ones it asks for.

The registry is the boundary between a language model's requests and code that
actually does something. Everything crossing it is untrusted: the model chooses
which tool to call, invents the arguments, and is perfectly capable of naming a
tool that does not exist or emitting arguments that are not JSON.

So the rule here is that :meth:`ToolRegistry.run` never raises. A tool that
fails returns a sentence explaining the failure, which the model can apologise
for or work around. An exception would instead escape into the streaming loop
and kill the turn, leaving the user with silence -- the failure mode Bruno spent a
whole step eliminating.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Final

from core.protocols import ToolCall, ToolResult

logger = logging.getLogger(__name__)

# A tool that takes longer than this has failed as far as the user is
# concerned: they asked a question out loud and are waiting for an answer.
DEFAULT_TIMEOUT_SECONDS: Final = 10.0


@dataclass(frozen=True, slots=True)
class Tool:
    """One capability the model can invoke.

    Attributes:
        name: Identifier the model uses. Lowercase with underscores.
        description: What it does and when to use it. This is the only thing
            the model reads when deciding, so it is prompt engineering rather
            than documentation -- vague wording here produces a tool that is
            called at the wrong moments or never at all.
        parameters: JSON Schema for the arguments. Default is no arguments,
            which is the most reliable kind of tool: nothing to get wrong.
        run: Implementation. Receives parsed arguments, returns a result.
    """

    name: str
    description: str
    run: Callable[[dict[str, Any]], ToolResult]
    parameters: dict[str, Any] = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )

    def spec(self) -> dict[str, Any]:
        """This tool in the shape the chat completions API expects."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Holds the available tools. Satisfies :class:`~bruno.core.protocols.Toolbox`.

    Args:
        tools: Capabilities to expose. An empty registry is valid and means
            Bruno is a pure conversationalist.
    """

    def __init__(self, tools: Iterable[Tool] = ()) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            self.add(tool)

    def add(self, tool: Tool) -> None:
        """Register a tool, replacing any tool of the same name."""
        if tool.name in self._tools:
            logger.warning("Replacing already-registered tool %r", tool.name)
        self._tools[tool.name] = tool

    @property
    def names(self) -> list[str]:
        """Registered tool names, for logs and diagnostics."""
        return sorted(self._tools)

    def __len__(self) -> int:
        return len(self._tools)

    def specs(self) -> list[dict[str, Any]]:
        """Every tool, described for the model."""
        return [tool.spec() for tool in self._tools.values()]

    def run(self, call: ToolCall) -> ToolResult:
        """Execute one call from the model.

        Never raises. Every failure becomes a result the model can read.
        """
        tool = self._tools.get(call.name)
        if tool is None:
            # Models occasionally invent a plausible-sounding tool. Saying so
            # is more useful than failing, because it can then answer without
            # one.
            logger.warning("Model asked for unknown tool %r", call.name)
            return ToolResult(
                f"There is no tool called {call.name!r}. "
                f"Available tools: {', '.join(self.names) or 'none'}."
            )

        try:
            arguments = _parse_arguments(call.arguments)
        except ValueError as exc:
            logger.warning("Bad arguments for %s: %s", call.name, exc)
            return ToolResult(f"Those arguments were not valid JSON: {exc}")

        started = time.perf_counter()
        try:
            result = tool.run(arguments)
        except Exception as exc:  # noqa: BLE001 -- a broken tool must not end the turn
            logger.exception("Tool %s failed", call.name)
            return ToolResult(f"That did not work: {exc}")

        elapsed = (time.perf_counter() - started) * 1000
        logger.info(
            "Tool %s ran in %.0f ms (%d image(s))", call.name, elapsed, len(result.images)
        )
        return result


def _parse_arguments(raw: str) -> dict[str, Any]:
    """Parse the model's argument blob.

    Raises:
        ValueError: If it is not a JSON object.
    """
    text = (raw or "").strip()
    if not text:
        return {}

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(str(exc)) from exc

    # A tool with no parameters is commonly called with a literal null, or an
    # empty string, rather than an empty object. Treating that as malformed
    # meant the tool never ran: the model would retry, get rejected again, and
    # eventually answer without ever having looked -- which reads as Bruno simply
    # ignoring what it was asked.
    if parsed is None:
        return {}

    if not isinstance(parsed, dict):
        raise ValueError(f"expected an object, got {type(parsed).__name__}")
    return parsed
