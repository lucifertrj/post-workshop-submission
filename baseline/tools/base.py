"""Base tool abstraction."""
from __future__ import annotations
import abc
from typing import Any, Dict

class BaseTool(abc.ABC):
    """Abstract base class for all tools."""
    
    name: str
    description: str
    
    @abc.abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool asynchronously with given arguments."""
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
            }
        }
