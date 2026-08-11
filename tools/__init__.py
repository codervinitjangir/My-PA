"""Things Bruno can do besides talk.

Each capability is one small module exposing a :class:`~bruno.tools.registry.Tool`.
The language model is told what exists and decides when to use it, which is the
difference between a companion and a command line: "what am I looking at",
"read this for me", and "can you see this" all reach the screen without anyone
writing a rule that matches those words.

Nothing here runs on its own. A tool executes only when the model asks for it
in response to something the user said, which keeps the promise Bruno was built
on -- the screen is looked at when you ask about it and at no other time.
"""

from tools.registry import Tool, ToolRegistry

__all__ = ["Tool", "ToolRegistry"]
