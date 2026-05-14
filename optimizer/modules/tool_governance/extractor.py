"""
Tool Necessity Extractor — estimates if a requested tool call is actually required.
"""
from __future__ import annotations
from typing import List, Any
from controller.state import AgentState, ToolCall
from .schema import ToolNecessitySignals, ToolNecessityScore

class ToolNecessityExtractor:
    """Estimates the necessity and expected utility of a tool call."""
    
    @staticmethod
    def _extract_signals(state: AgentState, tool_call: ToolCall) -> ToolNecessitySignals:
        # A real implementation would parse the question, thought, and tool input
        from controller.utils import get_last_step
        last_step = get_last_step(state)
        thought = last_step.thought.lower() if last_step else ""
            
        tool_input = str(tool_call.tool_input).lower()
        
        # Simple heuristics
        arithmetic = 1.0 if any(op in tool_input for op in ["+", "-", "*", "/", "sum"]) else 0.0
        retrieval = 1.0 if "search" in tool_call.tool_name.lower() or "who" in thought else 0.0
        uncertainty = 1.0 if "maybe" in thought or "not sure" in thought else 0.0
        
        # Sufficiency is high if we already took many steps
        sufficiency = min(1.0, len(state.steps) / 5.0)
        
        return ToolNecessitySignals(
            arithmetic_intensity=arithmetic,
            retrieval_intensity=retrieval,
            ambiguity_level=0.5,
            knowledge_uncertainty=uncertainty,
            reasoning_sufficiency=sufficiency
        )

    async def estimate(self, state: AgentState, tool_call: ToolCall) -> ToolNecessityScore:
        """Evaluate the state and requested tool to emit a structured necessity score."""
        signals = self._extract_signals(state, tool_call)
        
        expected_latency = 500.0
        expected_cost = 100
        expected_utility = 0.5
        
        if tool_call.tool_name.lower() in ["search", "wikipedia"]:
            expected_latency = 2000.0
            expected_cost = 500
            expected_utility = 0.8 if signals.knowledge_uncertainty > 0.5 else 0.2
        elif tool_call.tool_name.lower() in ["calculator", "math"]:
            expected_latency = 50.0
            expected_cost = 10
            expected_utility = 0.9 if signals.arithmetic_intensity > 0.0 else 0.1
            
        # If we have high reasoning sufficiency and low uncertainty, utility drops
        if signals.reasoning_sufficiency > 0.8 and signals.knowledge_uncertainty < 0.3:
            expected_utility *= 0.5
            
        is_required = expected_utility > 0.4
        
        return ToolNecessityScore(
            tool_name=tool_call.tool_name,
            is_required=is_required,
            expected_utility=expected_utility,
            expected_cost_tokens=expected_cost,
            expected_latency_ms=expected_latency,
            expected_confidence_gain=expected_utility * 0.5,
            signals=signals,
            estimator_name="heuristic_tool_estimator"
        )
