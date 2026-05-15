"""
Early Stopping Policy Engine.
"""
from __future__ import annotations
from controller.state import AgentState
from infrastructure.config.profile_manager import ProfileManager
from .schema import ConfidenceScore, StopDecision

class EarlyStoppingPolicy:
    """Evaluates confidence scores to determine if execution should truncate."""
    
    def __init__(self, stop_threshold: float | None = None, min_steps: int | None = None):
        # Resolve from profile if not explicitly overridden
        self.stop_threshold = stop_threshold or ProfileManager.resolve_threshold("stop_threshold", 0.7)
        self.min_steps = min_steps if min_steps is not None else ProfileManager.resolve_threshold("min_steps", 1)
        
    def evaluate(self, state: AgentState, score: ConfidenceScore) -> StopDecision:
        """Determine if we should stop early based on confidence."""
        
        # Use calibrated threshold if available
        threshold = state.calibration_context.get("stop_threshold", self.stop_threshold)
        
        if state.step_count < self.min_steps:
            return StopDecision(
                should_stop=False,
                reason="Minimum steps safeguard not met.",
                confidence_threshold_used=threshold,
                safeguards_triggered=True
            )
            
        if score.stop_confidence >= threshold:
            return StopDecision(
                should_stop=True,
                reason=f"Stop confidence {score.stop_confidence} exceeded threshold {threshold}.",
                confidence_threshold_used=threshold,
                safeguards_triggered=False
            )
            
        return StopDecision(
            should_stop=False,
            reason="Confidence threshold not reached.",
            confidence_threshold_used=threshold,
            safeguards_triggered=False
        )

    def propose(self, state: AgentState, score: ConfidenceScore) -> Optional[OptimizerProposal]:
        from optimizer.modules.arbitrator.schema import OptimizerProposal, OptimizerAction
        
        decision = self.evaluate(state, score)
        if decision.should_stop:
            return OptimizerProposal(
                optimizer_name="confidence_runtime",
                action=OptimizerAction.STOP,
                confidence=score.stop_confidence,
                reason=decision.reason,
                metadata={"score": score.model_dump(), "decision": decision.model_dump()}
            )
        return None
