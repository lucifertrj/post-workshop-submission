"""
Compute Budget Allocation Schema — Defines structured resource limits.
"""
from __future__ import annotations
import enum
from typing import Dict, Any, List
from pydantic import BaseModel, Field

class BudgetClass(str, enum.Enum):
    ULTRA_LOW = "ultra_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

class LatencyClass(str, enum.Enum):
    URGENT = "urgent"      # < 1s
    FAST = "fast"          # < 3s
    STANDARD = "standard"  # < 10s
    DEEP = "deep"          # > 10s

class ComputeBudgetAllocation(BaseModel):
    """The structured output of a compute allocator."""
    budget_class: BudgetClass
    max_reasoning_depth: int          # Absolute ceiling (termination)
    soft_reasoning_budget: int        # Expected ceiling (early stopping targets this)
    expected_token_budget: int
    expected_tool_budget: int
    latency_class: LatencyClass
    confidence: float
    policy_name: str
    allocation_latency_ms: float
