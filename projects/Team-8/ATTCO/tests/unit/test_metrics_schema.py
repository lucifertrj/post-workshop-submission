"""Unit tests for the metrics schema."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from metrics.schema import MetricEvent, RunSummary


def test_metric_event_is_frozen():
    event = MetricEvent(
        experiment_id="exp-1",
        run_id="run-1",
        question_id="q-1",
        metric_name="latency_ms",
        value=123.4,
        unit="ms",
    )
    with pytest.raises(Exception):
        event.value = 999.0  # type: ignore[misc]


def test_metric_event_defaults():
    event = MetricEvent(
        experiment_id="exp-1",
        run_id="run-1",
        question_id="q-1",
        metric_name="tokens_total",
        value=512.0,
        unit="tokens",
    )
    assert event.event_id is not None
    assert event.tags == {}
    assert event.step is None


def test_run_summary_efficiency_ratio():
    summary = RunSummary(
        run_id="run-1",
        experiment_id="exp-1",
        total_questions=100,
        accuracy=0.72,
        latency_total_ms_mean=1200.0,
        latency_total_ms_p95=3400.0,
        tokens_input_mean=800.0,
        tokens_output_mean=400.0,
        step_count_mean=5.2,
        tool_call_count_mean=3.1,
        efficiency_ratio=0.72 / 1200.0,
    )
    assert summary.efficiency_ratio == pytest.approx(0.72 / 1200.0)
