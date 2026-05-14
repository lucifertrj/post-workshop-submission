"""Unit tests for controller AgentState schema."""
from __future__ import annotations

import pytest
from controller.state import AgentState, ReasoningStep, ToolCall


def test_agent_state_step_count():
    state = AgentState(
        experiment_id="exp-1",
        question_id="q-1",
        question="What is the capital of France?",
    )
    assert state.step_count == 0

    state.steps.append(
        ReasoningStep(step=1, thought="I need to look this up.", action="search")
    )
    assert state.step_count == 1


def test_agent_state_defaults():
    state = AgentState(
        experiment_id="exp-1",
        question_id="q-1",
        question="Test question?",
    )
    assert state.is_terminated is False
    assert state.final_answer is None
    assert state.total_tokens == 0
    assert state.run_id is not None


def test_tool_call_optional_fields():
    tc = ToolCall(tool_name="search", tool_input={"query": "Paris"})
    assert tc.tool_output is None
    assert tc.error is None
