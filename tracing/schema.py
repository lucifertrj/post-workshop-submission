"""
Trace Event Schema — canonical schema for all ATTCO trace events.
Every reasoning step, tool invocation, routing decision, and token
allocation is represented as a TraceEvent.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventClass(str, enum.Enum):
    REASONING_STEP      = "REASONING_STEP"
    TOOL_INVOCATION     = "TOOL_INVOCATION"
    ROUTING_DECISION    = "ROUTING_DECISION"
    CONFIDENCE_ESTIMATE = "CONFIDENCE_ESTIMATE"
    DIFFICULTY_PREDICTION = "DIFFICULTY_PREDICTION"
    BUDGET_ALLOCATION   = "BUDGET_ALLOCATION"
    TRUNCATION_EVENT    = "TRUNCATION_EVENT"
    TOOL_GATE_DECISION  = "TOOL_GATE_DECISION"
    ARBITRATION_DECISION = "ARBITRATION_DECISION"
    ARBITRATION_EVENT    = "ARBITRATION_EVENT"
    OPTIMIZER_PROPOSAL  = "OPTIMIZER_PROPOSAL"
    COMPRESSION_EVENT   = "COMPRESSION_EVENT"
    CALIBRATION_EVENT   = "CALIBRATION_EVENT"
    TOKEN_ALLOCATION    = "TOKEN_ALLOCATION"
    LATENCY_CHECKPOINT  = "LATENCY_CHECKPOINT"
    VERIFICATION_TRIGGER = "VERIFICATION_TRIGGER"
    TERMINATION_EVENT   = "TERMINATION_EVENT"


class TraceEvent(BaseModel):
    """Immutable trace event. Emitted by any ATTCO subsystem."""

    event_id: UUID = Field(default_factory=uuid4)
    experiment_id: str
    run_id: str
    question_id: str
    event_class: EventClass
    event_type: str
    step: int = 0
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)
    token_delta: int | None = None
    latency_ms: float | None = None
    model_id: str | None = None
    node_id: str | None = None
    runtime_profile: str | None = None

    model_config = {"frozen": True}
