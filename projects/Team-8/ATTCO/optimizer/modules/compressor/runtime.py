"""
Context Optimization Runtime — mutates the active state to optimize prompt overhead.
"""
from __future__ import annotations
import time
import uuid
from controller.state import AgentState, ReasoningStep
from .schema import CompressionDecision, CompressionStrategy, CompressionOutcome

class ContextOptimizerRuntime:
    """Executes trace compression and context window optimization."""
    
    async def optimize(self, state: AgentState, decision: CompressionDecision) -> AgentState:
        """Apply compression to the active state while preserving history."""
        start_time = time.perf_counter()
        
        # 1. Preserve full history if not already backed up
        if not state.full_history:
            state.full_history = [s.model_dump() for s in state.steps]
        else:
            # Append only the new steps to the full history
            current_full_len = len(state.full_history)
            if len(state.steps) > current_full_len:
                for i in range(current_full_len, len(state.steps)):
                    state.full_history.append(state.steps[i].model_dump())

        # 2. Reconstruct steps based on compression strategy
        from controller.utils import get_steps
        steps = get_steps(state)
        optimized_steps = []
        for i, strategy in enumerate(decision.strategies):
            if i >= len(steps): break
            original_step = steps[i]
            
            if strategy.compression_strategy == CompressionStrategy.RETAIN:
                optimized_steps.append(original_step)
            elif strategy.compression_strategy == CompressionStrategy.SUMMARIZE:
                # Use LLM to summarize the thought if it's long enough
                if len(original_step.thought) > 100:
                    from llm.wrapper import LLMWrapper
                    llm = LLMWrapper(provider="openai", model_id="gpt-4o-mini", temperature=0.0)
                    sum_messages = [
                        {"role": "system", "content": "Summarize the following reasoning step thought into a single concise sentence, preserving the core insight and any intermediate findings."},
                        {"role": "user", "content": original_step.thought}
                    ]
                    sum_resp = await llm.agenerate(sum_messages)
                    summary_text = sum_resp.choices[0].message.content or original_step.thought[:100]
                else:
                    summary_text = original_step.thought

                # Create a summarized proxy step
                summary_step = ReasoningStep(
                    step=original_step.step,
                    thought=f"[SUMMARY] {summary_text}",
                    action=original_step.action,
                    observation="[Compressed Trace Context]"
                )
                optimized_steps.append(summary_step)
            elif strategy.compression_strategy == CompressionStrategy.DROP:
                # Skip this step in the active context
                continue
                
        state.steps = [s.model_dump() if hasattr(s, "model_dump") else s for s in optimized_steps]
        
        latency = (time.perf_counter() - start_time) * 1000
        
        outcome = CompressionOutcome(
            compression_id=str(uuid.uuid4()),
            decision=decision,
            latency_ms=latency
        )
        
        state.compression_history.append(outcome.model_dump())
        
        return state
