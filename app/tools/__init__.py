from app.tools.registry import ToolRegistry
from app.tools.base_tool import BaseTool

# Dynamically load all tool plugins inside this directory
ToolRegistry.load_tools(__name__)
