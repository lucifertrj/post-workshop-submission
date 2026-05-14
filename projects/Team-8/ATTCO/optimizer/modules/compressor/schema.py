"""
Compression Schema — defines trace value and context optimization decisions.
"""
from __future__ import annotations
import enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class CompressionStrategy(str, enum.Enum):
    RETAIN = "retain"        # Keep the step as is
    SUMMARIZE = "summarize"  # Replace with a short summary
    DROP = "drop"            # Remove from active context (preserve in history)
    COLLAPSE = "collapse"    # Merge multiple redundant steps into one

class TraceValueScore(BaseModel):
    """Estimation of the utility of a reasoning step for future reasoning."""
    step_index: int
    importance_score: float                # 0-1 (1 = critical path)
    redundancy_score: float                # 0-1 (1 = highly redundant)
    context_utility: float                 # Estimated value for prompt
    is_critical: bool
    compression_strategy: CompressionStrategy

class CompressionDecision(BaseModel):
    """The decision for how to optimize the active context."""
    strategies: List[TraceValueScore]
    original_token_estimate: int
    compressed_token_estimate: int
    compression_ratio: float
    rationale: str

class CompressionOutcome(BaseModel):
    """The result of a context optimization pass."""
    compression_id: str
    decision: CompressionDecision
    latency_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
