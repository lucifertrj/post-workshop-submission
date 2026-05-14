"""
Base Allocation Policy Interface.
"""
from __future__ import annotations
import abc
from typing import Any
from ..schema import ComputeBudgetAllocation
from intelligence.difficulty.schema import DifficultyPrediction

class BaseAllocationPolicy(abc.ABC):
    """Abstract base class for compute budget allocation policies."""
    
    name: str

    @abc.abstractmethod
    async def allocate(self, difficulty: DifficultyPrediction, **kwargs: Any) -> ComputeBudgetAllocation:
        """Map difficulty to a structured compute budget."""
        pass
