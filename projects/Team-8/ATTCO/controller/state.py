"""
Agent State Schema — the single source of truth for LangGraph node state.
All controller nodes read from and write to this schema exclusively.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    tool_name: str
    tool_input: dict[str, Any]
    tool_output: str | None = None
    error: str | None = None
    latency_ms: float | None = None


class ReasoningStep(BaseModel):
    step: int
    thought: str
    action: str | None = None
    observation: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tokens_used: int = 0
    latency_ms: float | None = None


class AgentState(BaseModel):
    """
    Mutable state threaded through all LangGraph nodes.
    Immutable fields (run_id, experiment_id) are set at initialization.
    """

    run_id: UUID = Field(default_factory=uuid4)
    experiment_id: str
    question_id: str
    question: str

    steps: list[dict[str, Any]] = Field(default_factory=list)
    reasoning_history: list[dict[str, Any]] = Field(default_factory=list)
    final_answer: str | None = None
    is_terminated: bool = False
    termination_cause: str | None = None

    total_tokens: int = 0
    total_latency_ms: float = 0.0

    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)
    arbitration_history: list[dict[str, Any]] = Field(default_factory=list)
    verification_history: list[dict[str, Any]] = Field(default_factory=list)
    compression_history: list[dict[str, Any]] = Field(default_factory=list)
    full_history: list[dict[str, Any]] = Field(default_factory=list)
    calibration_context: dict[str, Any] = Field(default_factory=dict)

    @property
    def step_count(self) -> int:
        return len(self.steps)
