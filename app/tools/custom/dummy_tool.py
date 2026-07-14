from app.tools.base_tool import BaseTool

class DummyTool(BaseTool):
    name = "dummy_tool"
    description = "I am a dummy tool"
    
    def execute(self, **kwargs):
        return "Dummy output"
