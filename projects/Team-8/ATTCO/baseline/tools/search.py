"""Dummy search tool for baseline testing."""
from __future__ import annotations
import asyncio
from typing import Any
from .base import BaseTool
from .registry import default_registry

class DummySearchTool(BaseTool):
    name = "Search"
    description = "Searches the web for information."

    async def execute(self, query: str, **kwargs: Any) -> str:
        # Simulate network delay
        await asyncio.sleep(0.5)
        return f"Mock search result for '{query}'"

# Register on module import
default_registry.register(DummySearchTool())
