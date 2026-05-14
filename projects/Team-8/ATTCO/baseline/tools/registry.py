"""Tool registry interface."""
from __future__ import annotations
from typing import Dict, Optional, Type
from .base import BaseTool

class ToolRegistry:
    """Registry for managing and executing tools."""
    
    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        
    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        
    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)
        
    async def execute(self, name: str, **kwargs: Any) -> Any:
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool {name} not found in registry.")
        return await tool.execute(**kwargs)
        
    def get_all_schemas(self) -> list[Dict[str, Any]]:
        return [tool.get_schema() for tool in self._tools.values()]

# Global default registry
default_registry = ToolRegistry()
