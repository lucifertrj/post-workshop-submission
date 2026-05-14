"""
Confidence Extractor — assesses reasoning trajectory to estimate confidence.
"""
from __future__ import annotations
from typing import List
from controller.state import AgentState, ReasoningStep
from .schema import ConfidenceSignals, ConfidenceScore

class ConfidenceExtractor:
    """Extracts confidence signals from reasoning loops."""
    
    @staticmethod
    def _calculate_redundancy(steps: List[ReasoningStep]) -> float:
        """Measure if recent thoughts are highly overlapping."""
        if len(steps) < 2:
            return 0.0
        # Simple overlap heuristic for redundant loops
        t1 = set(steps[-1].thought.lower().split())
        t2 = set(steps[-2].thought.lower().split())
        if not t1 or not t2:
            return 0.0
        overlap = len(t1.intersection(t2)) / max(len(t1), len(t2))
        return float(overlap)
        
    @staticmethod
    def _detect_low_information(steps: List[ReasoningStep]) -> bool:
        """Detect if the last action yielded an error or useless observation."""
        if not steps:
            return False
        last = steps[-1]
        if last.observation and ("error" in last.observation.lower() or "not found" in last.observation.lower()):
            return True
        return False
        
    @staticmethod
    def _calculate_stability(steps: List[ReasoningStep]) -> float:
        """Measure if the agent is hovering around the same final answer but not outputting it."""
        if len(steps) < 3:
            return 0.0
        
        # Look for repeated identical actions/queries
        actions = [s.action.lower() for s in steps[-3:] if s.action]
        if len(actions) >= 2 and actions[-1] == actions[-2]:
            return 0.8 # High stability/looping
            
        return 0.0

    async def estimate(self, state: AgentState) -> ConfidenceScore:
        """Evaluate the state and emit a structured confidence score."""
        from controller.utils import get_steps
        steps = get_steps(state)
        
        redundancy = self._calculate_redundancy(steps)
        low_info = self._detect_low_information(steps)
        stability = self._calculate_stability(steps)
        
        signals = ConfidenceSignals(
            answer_stability=stability,
            reasoning_redundancy=redundancy,
            tool_result_consistency=0.5, # Placeholder for advanced tool tracking
            low_information_continuation=low_info
        )
        
        # Base confidence calculation
        # If the agent is looping (high redundancy, low info, stable action), confidence drops in continuing
        # Alternatively, if it has a stable answer, confidence in STOPPING increases.
        
        stop_confidence = 0.0
        
        # If it's repeating the same action and getting nowhere
        if redundancy > 0.7 and low_info:
            stop_confidence = 0.9 # We should probably stop, it's stuck
            
        # If it seems to have an answer but is hesitating (redundant but high stability)
        if stability > 0.7:
            stop_confidence = max(stop_confidence, 0.85)
            
        # Standard decay - if we're super deep without an answer, confidence drops
        sufficiency = 1.0 - (redundancy * 0.5)
        
        return ConfidenceScore(
            reasoning_sufficiency_confidence=sufficiency,
            stop_confidence=stop_confidence,
            signals=signals,
            estimator_name="heuristic_confidence_estimator"
        )
