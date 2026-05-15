"""Model registry for LiteLLM wrapper."""
from __future__ import annotations
from typing import Dict, Optional, Type
from .wrapper import LLMWrapper
import structlog

logger = structlog.get_logger(__name__)

class ModelRegistry:
    def __init__(self) -> None:
        self._models: Dict[str, LLMWrapper] = {}

    def register(self, alias: str, provider: str, model_id: str, **kwargs: Any) -> None:
        self._models[alias] = LLMWrapper(provider=provider, model_id=model_id, **kwargs)
        logger.info("model_registered", alias=alias, provider=provider, model_id=model_id)

    def get_model(self, alias: str) -> Optional[LLMWrapper]:
        return self._models.get(alias)

default_model_registry = ModelRegistry()

# Register some default models
default_model_registry.register("gpt4o", "openai", "gpt-4o")
default_model_registry.register("claude3", "anthropic", "claude-3-sonnet-20240229")
