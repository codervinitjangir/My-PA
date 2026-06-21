from app.tools.registry import ToolRegistry
from app.tools.image_tool import ImageGenerationTool
from app.tools.desktop_tool import DesktopAppTool

# Register core tools
ToolRegistry.register(ImageGenerationTool())
ToolRegistry.register(DesktopAppTool())
