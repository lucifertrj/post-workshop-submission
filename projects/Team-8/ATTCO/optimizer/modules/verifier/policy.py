"""
Verification Policy Engine — governs the selective activation of self-validation.
"""
from __future__ import annotations
from typing import Optional
from controller.state import AgentState
from infrastructure.config.profile_manager import ProfileManager
from optimizer.modules.arbitrator.schema import OptimizerProposal, OptimizerAction
from .schema import VerificationNecessityScore

class VerificationPolicy:
    """Decides if and when to trigger a verification pass."""
    
    def __init__(self, risk_threshold: float | None = None):
        self.risk_threshold = risk_threshold or ProfileManager.resolve_threshold("verification_risk_trigger", 0.5)

    def propose(self, state: AgentState, score: VerificationNecessityScore) -> Optional[OptimizerProposal]:
        """Propose a verification action if risk is high enough."""
        
        # Use calibrated threshold
        threshold = state.calibration_context.get("verification_threshold", self.risk_threshold)
        
        if score.risk_score >= threshold:
            return OptimizerProposal(
                optimizer_name="verification_governance",
                action=OptimizerAction.VERIFY,
                confidence=score.risk_score,
                reason=score.verification_reason,
                metadata={"score": score.model_dump()}
            )
            
        return None
