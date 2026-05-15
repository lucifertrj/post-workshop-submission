"""
Base Optimizer Interface — all optimizer modules must implement this ABC.
Optimizers are stateless, independently swappable, and config-driven.
"""
from __future__ import annotations

import abc
from typing import Any

from pydantic import BaseModel


class OptimizerConfig(BaseModel):
    """Base config for all optimizer modules."""
    enabled: bool = True
    name: str = "base"


class OptimizerDecision(BaseModel):
    """Decision returned by an optimizer after evaluating agent state."""
    should_continue: bool
    reason: str
    metadata: dict[str, Any] = {}


class BaseOptimizer(abc.ABC):
    """
    Abstract base for all ATTCO optimizer modules.

    Each optimizer receives the current agent state snapshot and returns
    an OptimizerDecision. Optimizers MUST NOT mutate state directly.
    They MUST NOT import from controller/, benchmarks/, or baseline/.
    """

    def __init__(self, config: OptimizerConfig) -> None:
        self.config = config

    @abc.abstractmethod
    async def evaluate(self, state_snapshot: dict[str, Any]) -> OptimizerDecision:
        """
        Evaluate the current agent state and return a routing decision.

        Args:
            state_snapshot: A serialized snapshot of AgentState fields.

        Returns:
            OptimizerDecision with continuation recommendation and rationale.
        """
        ...

    @property
    def name(self) -> str:
        return self.config.name

    def is_enabled(self) -> bool:
        return self.config.enabled
