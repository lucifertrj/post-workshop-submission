"""
Trace Value Engine — estimates the importance and redundancy of reasoning steps.
"""
from __future__ import annotations
from typing import List, Dict, Any
from controller.state import AgentState, ReasoningStep
from .schema import TraceValueScore, CompressionStrategy

class TraceValueEngine:
    """Estimates utility of trace segments for prompt optimization."""
    
    @staticmethod
    def _estimate_step_value(step: ReasoningStep, index: int, total: int) -> TraceValueScore:
        """Score an individual step based on content and position."""
        importance = 0.5
        redundancy = 0.0
        
        # 1. Criticality: Tool calls and their observations are generally critical
        if step.tool_calls:
            importance += 0.4
            
        # 2. Recency: Last 2 steps are always high importance for context
        if index >= total - 2:
            importance = 1.0
            
        # 3. Redundancy: Heuristic for repeating patterns (e.g., "I will search")
        if "search" in step.thought.lower() and index > 2:
            redundancy = 0.3
            
        strategy = CompressionStrategy.RETAIN
        if importance < 0.3:
            strategy = CompressionStrategy.DROP
        elif redundancy > 0.6:
            strategy = CompressionStrategy.SUMMARIZE
            
        return TraceValueScore(
            step_index=index,
            importance_score=importance,
            redundancy_score=redundancy,
            context_utility=importance * (1.0 - redundancy),
            is_critical=importance > 0.8,
            compression_strategy=strategy
        )

    async def analyze_trace(self, state: AgentState) -> List[TraceValueScore]:
        """Analyze the full trajectory and score each step."""
        from controller.utils import get_steps
        steps = get_steps(state)
        scores = []
        for i, step in enumerate(steps):
            scores.append(self._estimate_step_value(step, i, len(steps)))
        return scores
