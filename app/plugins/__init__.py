from app.tools.registry import ToolRegistry

# Dynamically load all plugins inside this package
ToolRegistry.load_tools(__name__)
