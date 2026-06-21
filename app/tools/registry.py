from typing import Dict, Type
from app.tools.base_tool import BaseTool

class ToolRegistry:
    """
    Central registry for all tools in the system.
    """
    _tools: Dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool: BaseTool):
        cls._tools[tool.name] = tool

    @classmethod
    def get_tool(cls, name: str) -> BaseTool:
        if name not in cls._tools:
            raise ValueError(f"Tool '{name}' not found in registry.")
        return cls._tools[name]

    @classmethod
    def list_tools(cls) -> Dict[str, str]:
        return {name: tool.description for name, tool in cls._tools.items()}
