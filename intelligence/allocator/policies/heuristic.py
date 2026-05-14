"""
Heuristic Allocation Policy.
Maps DifficultyPrediction to structured execution budgets.
"""
from __future__ import annotations
import time
from typing import Any
from .base import BaseAllocationPolicy
from .registry import default_policy_registry
from ..schema import ComputeBudgetAllocation, BudgetClass, LatencyClass
from intelligence.difficulty.schema import DifficultyPrediction, DifficultyClass

class HeuristicAllocationPolicy(BaseAllocationPolicy):
    name = "heuristic_allocator"

    async def allocate(self, difficulty: DifficultyPrediction, **kwargs: Any) -> ComputeBudgetAllocation:
        start_time = time.perf_counter()
        
        # Difficulty to Budget Mapping
        diff_class = difficulty.difficulty_class
        
        if diff_class == DifficultyClass.TRIVIAL:
            budget_class = BudgetClass.ULTRA_LOW
            latency_class = LatencyClass.URGENT
            max_depth = 3
            soft_depth = 2
            token_budget = 500
            tool_budget = 0
            
        elif diff_class == DifficultyClass.SIMPLE:
            budget_class = BudgetClass.LOW
            latency_class = LatencyClass.FAST
            max_depth = 4
            soft_depth = 3
            token_budget = 1000
            tool_budget = 1
            
        elif diff_class == DifficultyClass.MODERATE:
            budget_class = BudgetClass.MEDIUM
            latency_class = LatencyClass.STANDARD
            max_depth = 5
            soft_depth = 4
            token_budget = 2000
            tool_budget = 3
            
        elif diff_class == DifficultyClass.COMPLEX:
            budget_class = BudgetClass.HIGH
            latency_class = LatencyClass.DEEP
            max_depth = 7
            soft_depth = 5
            token_budget = 5000
            tool_budget = 6
            
        else: # EXTREME
            budget_class = BudgetClass.EXTREME
            latency_class = LatencyClass.DEEP
            max_depth = 12
            soft_depth = 8
            token_budget = 10000
            tool_budget = 12
            
        # Add multipliers based on expected features
        if difficulty.expected_tool_usage:
            tool_budget += 2
            token_budget = int(token_budget * 1.2)
            
        latency = (time.perf_counter() - start_time) * 1000

        return ComputeBudgetAllocation(
            budget_class=budget_class,
            max_reasoning_depth=max_depth,
            soft_reasoning_budget=soft_depth,
            expected_token_budget=token_budget,
            expected_tool_budget=tool_budget,
            latency_class=latency_class,
            confidence=0.85,
            policy_name=self.name,
            allocation_latency_ms=latency
        )

default_policy_registry.register(HeuristicAllocationPolicy())
