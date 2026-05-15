"""
Metrics Schema — Pydantic v2 definitions for all ATTCO metric events.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MetricEvent(BaseModel):
    """Atomic metric observation. Written to DuckDB/Parquet store."""

    event_id: UUID = Field(default_factory=uuid4)
    experiment_id: str
    run_id: str
    question_id: str
    metric_name: str
    value: float
    unit: str
    step: int | None = None
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow)
    tags: dict[str, str] = Field(default_factory=dict)
    runtime_profile: str | None = None

    model_config = {"frozen": True}


class RunSummary(BaseModel):
    """Aggregated metrics for a single benchmark run."""

    run_id: str
    experiment_id: str
    total_questions: int
    avg_accuracy: float
    avg_latency_ms: float
    avg_latency_p95: float
    avg_tokens: float
    avg_reasoning_depth: float
    avg_tool_calls: float
    efficiency_ratio: float   # accuracy / tokens_total_mean
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    runtime_profile: str = "unknown"
