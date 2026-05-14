"""
Self-Validation Runtime — executes selective reasoning verification passes.
"""
from __future__ import annotations
import time
from typing import Dict, Any
from controller.state import AgentState
from .schema import ValidationOutcome

class SelfValidationRuntime:
    """Executes verification logic to confirm reasoning correctness."""
    
    async def validate(self, state: AgentState) -> ValidationOutcome:
        """Perform a real verification pass using LLM."""
        start_time = time.perf_counter()
        
        from llm.wrapper import LLMWrapper
        llm = LLMWrapper(provider="openai", model_id="gpt-4o-mini", temperature=0.0)
        
        # Build verification prompt
        from controller.utils import get_steps
        steps = get_steps(state)
        history = "\n".join([f"Step {s.step}: {s.thought}" for s in steps])
        messages = [
            {"role": "system", "content": "You are a verification critic. Analyze the following reasoning steps for hallucinations, logical errors, or contradictions. Return 'VALID' if correct, or a detailed 'CRITIQUE' if issues are found."},
            {"role": "user", "content": f"Query: {state.question}\n\nReasoning History:\n{history}\n\nDoes this reasoning contain errors? Answer with VALID or CRITIQUE: <reason>"}
        ]
        
        response = await llm.agenerate(messages)
        content = response.choices[0].message.content or ""
        
        usage = response.usage
        tokens_used = (usage.prompt_tokens + usage.completion_tokens) if usage else 0
        latency = (time.perf_counter() - start_time) * 1000
        
        is_valid = "VALID" in content.upper() and "CRITIQUE" not in content.upper()
        critique = content.replace("CRITIQUE:", "").strip() if not is_valid else None
        
        return ValidationOutcome(
            is_valid=is_valid,
            critique=critique,
            confidence_delta=0.2 if is_valid else -0.3,
            validation_latency_ms=latency,
            validation_cost_tokens=tokens_used,
            metadata={"model": "gpt-4o-mini"}
        )
