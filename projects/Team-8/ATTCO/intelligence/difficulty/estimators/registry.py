"""
Registry for Difficulty Estimators.
"""
from __future__ import annotations
from typing import Dict, Optional
from .base import BaseDifficultyEstimator

class EstimatorRegistry:
    def __init__(self) -> None:
        self._estimators: Dict[str, BaseDifficultyEstimator] = {}

    def register(self, estimator: BaseDifficultyEstimator) -> None:
        self._estimators[estimator.name] = estimator

    def get_estimator(self, name: str) -> Optional[BaseDifficultyEstimator]:
        return self._estimators.get(name)

default_estimator_registry = EstimatorRegistry()
