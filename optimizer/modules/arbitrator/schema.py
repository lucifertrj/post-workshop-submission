"""
Arbitration Schema — defines structured optimizer proposals and unified decisions.
"""
from __future__ import annotations
import enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class OptimizerAction(str, enum.Enum):
    CONTINUE = "continue"
    STOP = "stop"
    SUPPRESS_TOOL = "suppress_tool"
    REQUEST_TOOL = "request_tool"
    TRUNCATE = "truncate"
    VERIFY = "verify"

class OptimizerProposal(BaseModel):
    """A proposal from a specific optimizer module."""
    optimizer_name: str
    action: OptimizerAction
    confidence: float
    reason: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ArbitrationDecision(BaseModel):
    """The final decision after resolving optimizer conflicts."""
    final_action: OptimizerAction
    winning_optimizer: str
    overridden_proposals: List[OptimizerProposal]
    rationale: str
    arbitration_latency_ms: float
    governance_metadata: Dict[str, Any] = Field(default_factory=dict)

class ArbitrationHistory(BaseModel):
    """History of decisions for a single query trajectory."""
    decisions: List[ArbitrationDecision] = Field(default_factory=list)
