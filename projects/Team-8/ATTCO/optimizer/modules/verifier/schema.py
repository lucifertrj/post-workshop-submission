"""
Verification Schema — defines correctness risk signals and validation outcomes.
"""
from __future__ import annotations
import enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class CorrectnessRiskSignals(BaseModel):
    """Signals indicating potential reasoning errors or hallucinations."""
    reasoning_volatility: float = 0.0      # Sudden drops/spikes in confidence
    answer_inconsistency: float = 0.0      # Oscillating between different answers
    tool_contradiction: float = 0.0        # Tool output contradicts previous thought
    uncertainty_depth: float = 0.0         # Accumulation of "maybe/not sure" over steps
    trajectory_instability: float = 0.0    # Frequency of self-corrections

class VerificationNecessityScore(BaseModel):
    """Estimation of whether a verification pass is required."""
    risk_score: float                      # Combined risk estimate (0-1)
    is_required: bool
    expected_utility: float
    verification_reason: str
    signals: CorrectnessRiskSignals

class ValidationOutcome(BaseModel):
    """The result of a self-validation execution."""
    is_valid: bool
    critique: Optional[str] = None
    confidence_delta: float
    validation_latency_ms: float
    validation_cost_tokens: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
