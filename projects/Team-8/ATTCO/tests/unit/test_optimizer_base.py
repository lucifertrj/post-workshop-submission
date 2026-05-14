"""Unit tests for the optimizer base contract."""
from __future__ import annotations

import pytest
from optimizer.base import BaseOptimizer, OptimizerConfig, OptimizerDecision


class _ConcreteOptimizer(BaseOptimizer):
    async def evaluate(self, state_snapshot: dict) -> OptimizerDecision:
        return OptimizerDecision(should_continue=True, reason="test")


def test_optimizer_is_enabled_by_default():
    opt = _ConcreteOptimizer(OptimizerConfig(name="test"))
    assert opt.is_enabled() is True


def test_optimizer_disabled_via_config():
    opt = _ConcreteOptimizer(OptimizerConfig(name="test", enabled=False))
    assert opt.is_enabled() is False


@pytest.mark.asyncio
async def test_optimizer_returns_decision():
    opt = _ConcreteOptimizer(OptimizerConfig(name="test"))
    decision = await opt.evaluate({"step": 1, "total_tokens": 100})
    assert isinstance(decision, OptimizerDecision)
    assert decision.should_continue is True


def test_optimizer_name():
    opt = _ConcreteOptimizer(OptimizerConfig(name="depth_controller"))
    assert opt.name == "depth_controller"
