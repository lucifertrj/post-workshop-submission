"""
Verification Risk Engine — extracts signals to estimate reasoning correctness risk.
"""
from __future__ import annotations
from typing import List, Dict, Any
from controller.state import AgentState
from .schema import CorrectnessRiskSignals, VerificationNecessityScore

class VerificationRiskEngine:
    """Estimates the likelihood of hallucinations or reasoning errors."""
    
    @staticmethod
    def _calculate_volatility(trajectory: List[Dict[str, Any]]) -> float:
        """Measure sudden shifts in confidence scores."""
        if len(trajectory) < 2:
            return 0.0
        
        confidences = [t.get("stop_confidence", 0.0) for t in trajectory]
        diffs = [abs(confidences[i] - confidences[i-1]) for i in range(1, len(confidences))]
        return sum(diffs) / len(diffs)

    async def estimate_risk(self, state: AgentState) -> VerificationNecessityScore:
        """Evaluate the state trajectory and emit a necessity score."""
        trajectory = state.metadata.get("confidence_trajectory", [])
        
        volatility = self._calculate_volatility(trajectory)
        
        # Simple inconsistency check: if recent thoughts contain contradictions
        inconsistency = 0.0
        from controller.utils import get_steps
        steps = get_steps(state)
        if len(steps) >= 2:
            last = steps[-1].thought.lower()
            prev = steps[-2].thought.lower()
            # If agent says "actually" or "correction" or "instead"
            if any(word in last for word in ["actually", "correction", "instead", "wait"]):
                inconsistency = 0.7
                
        signals = CorrectnessRiskSignals(
            reasoning_volatility=volatility,
            answer_inconsistency=inconsistency,
            tool_contradiction=0.0, # Placeholder
            uncertainty_depth=min(1.0, len(state.steps) / 10.0),
            trajectory_instability=(volatility + inconsistency) / 2.0
        )
        
        # Combined risk score
        risk_score = min(1.0, (signals.reasoning_volatility * 0.4 + 
                               signals.answer_inconsistency * 0.4 + 
                               signals.uncertainty_depth * 0.2))
                               
        return VerificationNecessityScore(
            risk_score=risk_score,
            is_required=risk_score > 0.5,
            expected_utility=risk_score * 0.8,
            verification_reason=f"Risk score {risk_score:.2f} (volatility: {volatility:.2f}, inconsistency: {inconsistency:.2f})",
            signals=signals
        )
