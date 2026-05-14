"""
Research Schema — defines experiment suites, ablations, and attribution reports.
"""
from __future__ import annotations
import enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class OptimizerToggles(BaseModel):
    """Flags to enable/disable specific optimization layers."""
    depth_controller: bool = True
    early_stopping: bool = True
    tool_gating: bool = True
    compression: bool = True
    verification: bool = True
    arbitration: bool = True

class AblationConfig(BaseModel):
    """Configuration for an ablation study run."""
    experiment_id: str
    description: str
    toggles: OptimizerToggles
    overrides: Dict[str, Any] = Field(default_factory=dict)

class OptimizerContribution(BaseModel):
    """The estimated impact of a single optimizer on the run."""
    optimizer_name: str
    token_savings: int
    latency_savings_ms: float
    accuracy_impact: float
    verification_overhead_ms: float
    intervention_count: int

class AttributionReport(BaseModel):
    """Global report attributing gains to specific optimizers."""
    experiment_id: str
    contributions: List[OptimizerContribution]
    cumulative_token_reduction: float
    cumulative_latency_reduction: float
    pareto_score: float

class ExperimentSweep(BaseModel):
    """Definition of a parameter sweep experiment."""
    sweep_id: str
    parameter_name: str
    values: List[Any]
    base_config: AblationConfig
