"""
Calibration Schema — defines policy parameters, snapshots, and calibration decisions.
"""
from __future__ import annotations
import enum
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ParameterCategory(str, enum.Enum):
    CONFIDENCE = "confidence"
    VERIFICATION = "verification"
    TOOL_GATING = "tool_gating"
    COMPRESSION = "compression"
    ARBITRATION = "arbitration"

class PolicyParameter(BaseModel):
    """A tunable parameter for an optimization policy."""
    name: str
    category: ParameterCategory
    current_value: float
    default_value: float
    min_value: float
    max_value: float
    description: str

class CalibrationDecision(BaseModel):
    """The decision to adjust policy parameters based on telemetry."""
    parameter_updates: Dict[str, float]
    rationale: str
    metrics_baseline: Dict[str, float]
    adaptation_timestamp: datetime = Field(default_factory=datetime.now)

class PolicySnapshot(BaseModel):
    """A versioned snapshot of all adaptive parameters."""
    version_id: str
    parameters: List[PolicyParameter]
    created_at: datetime = Field(default_factory=datetime.now)
    parent_version_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
