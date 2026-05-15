"""
Token Budget Optimizer — stub.
Terminates reasoning when token budget is exhausted.
"""
from __future__ import annotations
from typing import Any
from infrastructure.config.profile_manager import ProfileManager
from optimizer.base import BaseOptimizer, OptimizerConfig, OptimizerDecision
from optimizer.registry import register


class TokenBudgetConfig(OptimizerConfig):
    name: str = "token_budget"
    budget_tokens: int | None = None
    soft_limit_fraction: float = 0.85


@register("token_budget")
class TokenBudgetOptimizer(BaseOptimizer):
    """Terminates when token consumption exceeds configured budget."""

    def __init__(self, config: TokenBudgetConfig) -> None:
        super().__init__(config)
        self._cfg = config

    async def evaluate(self, state_snapshot: dict[str, Any]) -> OptimizerDecision:
        used = state_snapshot.get("total_tokens", 0)
        limit = self._cfg.budget_tokens or ProfileManager.resolve_threshold("budget_tokens", 4096)
        if used >= limit:
            return OptimizerDecision(
                should_continue=False,
                reason=f"Token budget {limit} exhausted (used={used})",
            )
        return OptimizerDecision(
            should_continue=True,
            reason=f"Tokens OK ({used}/{limit})",
        )
