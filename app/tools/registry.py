import pkgutil
import importlib
import inspect
import logging
from typing import Dict, Type
from app.tools.base_tool import BaseTool

logger = logging.getLogger("J.A.R.V.I.S")

class ToolRegistry:
    """
    Central registry for all tools in the system.
    Dynamically loads tool plugins from the tools directory.
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

    @classmethod
    def load_tools(cls, package_name: str = "app.tools"):
        """Dynamically discovers and registers all tools in the given package."""
        logger.info(f"[TOOL REGISTRY] Loading tools from {package_name}...")
        try:
            package = importlib.import_module(package_name)
            for _, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
                if not is_pkg and module_name != f"{package_name}.base_tool" and module_name != f"{package_name}.registry":
                    try:
                        module = importlib.import_module(module_name)
                        for name, obj in inspect.getmembers(module):
                            if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj is not BaseTool:
                                tool_instance = obj()
                                if tool_instance.name not in cls._tools:
                                    cls.register(tool_instance)
                                    logger.info(f"[TOOL REGISTRY] Registered: {tool_instance.name}")
                    except Exception as e:
                        logger.warning(f"[TOOL REGISTRY] Failed to load tool from {module_name}: {e}")
        except Exception as e:
            logger.error(f"[TOOL REGISTRY] Failed to load package {package_name}: {e}")
