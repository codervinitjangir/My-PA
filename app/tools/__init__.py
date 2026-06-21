from app.tools.registry import ToolRegistry
from app.tools.image_tool import ImageGenerationTool
from app.tools.desktop_tool import DesktopAppTool
from app.tools.mcp_client import MCPClientTool
from app.tools.browser_tool import AdvancedBrowserTool

# Register core tools
ToolRegistry.register(ImageGenerationTool())
ToolRegistry.register(DesktopAppTool())
ToolRegistry.register(MCPClientTool())
ToolRegistry.register(AdvancedBrowserTool())
