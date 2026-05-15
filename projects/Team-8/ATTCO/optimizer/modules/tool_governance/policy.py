"""
Tool Gating Policy Engine.
"""
from __future__ import annotations
from controller.state import AgentState
from infrastructure.config.profile_manager import ProfileManager
from .schema import ToolNecessityScore, ToolGateDecision

class ToolGatingPolicy:
    """Evaluates tool necessity scores to determine if execution should be suppressed."""
    
    def __init__(self, utility_threshold: float | None = None, max_cost: int = 1000):
        self.utility_threshold = utility_threshold or ProfileManager.resolve_threshold("utility_threshold", 0.5)
        self.max_cost = max_cost
        
    def evaluate(self, state: AgentState, score: ToolNecessityScore) -> ToolGateDecision:
        """Determine if we should suppress the tool call."""
        
        # Use calibrated threshold
        threshold = state.calibration_context.get("utility_threshold", self.utility_threshold)
        
        # Suppress if expected utility is too low
        if score.expected_utility < threshold:
            return ToolGateDecision(
                tool_name=score.tool_name,
                should_suppress=True,
                reason=f"Expected utility {score.expected_utility:.2f} is below threshold {threshold:.2f}.",
                policy_name="heuristic_tool_gater",
                safeguards_triggered=False
            )
            
        # Suppress if too expensive
        if score.expected_cost_tokens > self.max_cost:
            return ToolGateDecision(
                tool_name=score.tool_name,
                should_suppress=True,
                reason=f"Expected cost {score.expected_cost_tokens} exceeds maximum {self.max_cost}.",
                policy_name="heuristic_tool_gater",
                safeguards_triggered=True
            )
            
        return ToolGateDecision(
            tool_name=score.tool_name,
            should_suppress=False,
            reason="Tool necessity verified.",
            policy_name="heuristic_tool_gater",
            safeguards_triggered=False
        )

    def propose(self, state: AgentState, score: ToolNecessityScore) -> Optional[OptimizerProposal]:
        from optimizer.modules.arbitrator.schema import OptimizerProposal, OptimizerAction
        
        decision = self.evaluate(state, score)
        if decision.should_suppress:
            return OptimizerProposal(
                optimizer_name="tool_governance",
                action=OptimizerAction.SUPPRESS_TOOL,
                confidence=1.0 - score.expected_utility,
                reason=decision.reason,
                metadata={"score": score.model_dump(), "decision": decision.model_dump()}
            )
        return None
