"""
Confidence Schema — defines structured confidence signals and stopping decisions.
"""
from __future__ import annotations
from typing import Dict, Any, List
from pydantic import BaseModel, Field

class ConfidenceSignals(BaseModel):
    """Signals extracted from the reasoning trajectory."""
    answer_stability: float = 0.0          # How often the same provisional answer appears
    reasoning_redundancy: float = 0.0      # Overlap between consecutive thoughts
    tool_result_consistency: float = 0.0   # Are tools returning expected/consistent types
    low_information_continuation: bool = False # Did the last step add no new information?

class ConfidenceScore(BaseModel):
    """The structured output of a confidence estimator."""
    reasoning_sufficiency_confidence: float # Overall confidence that we have enough info
    stop_confidence: float                  # Confidence that we should stop NOW
    signals: ConfidenceSignals
    estimator_name: str

class StopDecision(BaseModel):
    """The structured decision output of a stopping policy."""
    should_stop: bool
    reason: str
    confidence_threshold_used: float
    safeguards_triggered: bool
