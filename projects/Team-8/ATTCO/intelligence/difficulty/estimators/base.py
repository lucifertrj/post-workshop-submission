"""
Base Difficulty Estimator Interface.
"""
from __future__ import annotations
import abc
from typing import Any
from ..schema import DifficultyPrediction

class BaseDifficultyEstimator(abc.ABC):
    """Abstract base class for all query difficulty estimators."""
    
    name: str

    @abc.abstractmethod
    async def estimate(self, query: str, **kwargs: Any) -> DifficultyPrediction:
        """Estimate the difficulty of a query."""
        pass
