"""
Tool Governance Schema — defines tool necessity estimation and gating decisions.
"""
from __future__ import annotations
from typing import Dict, Any, List
from pydantic import BaseModel, Field

class ToolNecessitySignals(BaseModel):
    """Signals extracted from the reasoning trajectory concerning tool usage."""
    arithmetic_intensity: float = 0.0
    retrieval_intensity: float = 0.0
    ambiguity_level: float = 0.0
    knowledge_uncertainty: float = 0.0
    reasoning_sufficiency: float = 0.0

class ToolNecessityScore(BaseModel):
    """The structured output of a tool-necessity estimator."""
    tool_name: str
    is_required: bool
    expected_utility: float
    expected_cost_tokens: int
    expected_latency_ms: float
    expected_confidence_gain: float
    signals: ToolNecessitySignals
    estimator_name: str

class ToolGateDecision(BaseModel):
    """The structured decision output of a tool gating policy."""
    tool_name: str
    should_suppress: bool
    reason: str
    policy_name: str
    safeguards_triggered: bool
