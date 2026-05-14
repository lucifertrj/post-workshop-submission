"""
Optimizer Registry — central registry for all optimizer modules.
Supports dynamic registration and config-driven instantiation.
"""
from __future__ import annotations

from typing import Type

import structlog

from optimizer.base import BaseOptimizer, OptimizerConfig

logger = structlog.get_logger(__name__)

_REGISTRY: dict[str, Type[BaseOptimizer]] = {}


def register(name: str) -> object:
    """Decorator to register an optimizer class by name."""
    def decorator(cls: Type[BaseOptimizer]) -> Type[BaseOptimizer]:
        if name in _REGISTRY:
            logger.warning("optimizer_overwritten", name=name)
        _REGISTRY[name] = cls
        logger.debug("optimizer_registered", name=name)
        return cls
    return decorator


def build(name: str, config: OptimizerConfig) -> BaseOptimizer:
    """Instantiate a registered optimizer by name with given config."""
    if name not in _REGISTRY:
        raise KeyError(f"Optimizer '{name}' not registered. Available: {list(_REGISTRY)}")
    return _REGISTRY[name](config)


def available() -> list[str]:
    return list(_REGISTRY.keys())
