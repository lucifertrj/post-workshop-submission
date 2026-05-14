"""
Heuristic Difficulty Estimator.
Uses structural features to predict complexity via heuristics.
"""
from __future__ import annotations
import time
from typing import Any
from .base import BaseDifficultyEstimator
from .registry import default_estimator_registry
from ..schema import DifficultyPrediction, DifficultyClass, ComplexityCategory
from ..features import FeatureExtractor

class HeuristicEstimator(BaseDifficultyEstimator):
    name = "heuristic_estimator"

    def __init__(self) -> None:
        self.extractor = FeatureExtractor()

    async def estimate(self, query: str, **kwargs: Any) -> DifficultyPrediction:
        start_time = time.perf_counter()
        features = self.extractor.extract(query)
        
        # Heuristic rules
        complexity_categories = []
        depth = 1
        tool_usage = False
        compute = 500
        
        if features.arithmetic_indicators > 0:
            complexity_categories.append(ComplexityCategory.ARITHMETIC)
            depth += 1
            tool_usage = True
            
        if features.multi_hop_indicators > 0:
            complexity_categories.append(ComplexityCategory.MULTI_HOP)
            depth += 2
            tool_usage = True
            
        if features.retrieval_indicators > 0:
            complexity_categories.append(ComplexityCategory.RETRIEVAL_HEAVY)
            tool_usage = True
            
        if features.comparison_indicators > 0:
            complexity_categories.append(ComplexityCategory.COMPARISON)
            depth += 1
            
        if features.ambiguity_indicators > 0:
            complexity_categories.append(ComplexityCategory.AMBIGUOUS)
            depth += 1
            
        if features.symbolic_indicators > 0:
            complexity_categories.append(ComplexityCategory.SYMBOLIC)
            depth += 2
        
        # Difficulty classes
        if depth <= 1:
            diff_class = DifficultyClass.TRIVIAL
            compute = 300
        elif depth == 2:
            diff_class = DifficultyClass.SIMPLE
            compute = 800
        elif depth == 3:
            diff_class = DifficultyClass.MODERATE
            compute = 1500
        elif depth <= 5:
            diff_class = DifficultyClass.COMPLEX
            compute = 3000
        else:
            diff_class = DifficultyClass.EXTREME
            compute = 5000
            
        latency = (time.perf_counter() - start_time) * 1000

        return DifficultyPrediction(
            difficulty_class=diff_class,
            complexity_categories=complexity_categories,
            expected_reasoning_depth=depth,
            expected_tool_usage=tool_usage,
            expected_compute_tokens=compute,
            confidence=0.8, # Static confidence for heuristic
            features=features,
            estimator_name=self.name,
            latency_ms=latency
        )

default_estimator_registry.register(HeuristicEstimator())
