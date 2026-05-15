"""Terminate node — emit final answer and close state."""
from __future__ import annotations
from datetime import datetime
from controller.state import AgentState
import structlog
logger = structlog.get_logger(__name__)


async def terminate_node(state: AgentState) -> AgentState:
    """Mark state as terminated with timestamp and perform final synthesis if needed."""
    
    # If final_answer is placeholder or missing, perform synthesis
    is_placeholder = state.final_answer and any(x in state.final_answer.lower() for x in ["truncated", "halted", "ceiling"])
    
    if not state.final_answer or is_placeholder:
        logger.info("performing_final_synthesis", run_id=state.run_id)
        
        from llm.wrapper import LLMWrapper
        llm = LLMWrapper(provider="openai", model_id="gpt-4o", temperature=0.0)
        
        # Build context from reasoning_history if available, else steps
        source = state.reasoning_history if state.reasoning_history else [s.model_dump() for s in state.steps]
        
        context_parts = []
        for i, s in enumerate(source):
            part = f"Step {i+1}: {s.get('thought')}\n"
            if s.get('action'):
                part += f"Action: {s.get('action')}\n"
            if s.get('observation'):
                part += f"Observation: {s.get('observation')}\n"
            context_parts.append(part)
            
        context = "\n".join(context_parts)
        
        prompt = f"""
        You are an AI agent that was interrupted during reasoning by an adaptive orchestration system.
        Based on the partial reasoning trajectory provided below, synthesize a concise and accurate final answer to the original question.
        If the information is incomplete, provide the best possible partial answer based on the evidence found so far.
        
        Reasoning History:
        {context}
        
        Original Question: {state.question}
        
        Final Answer:
        """
        
        try:
            response = await llm.agenerate([{"role": "user", "content": prompt}])
            state.final_answer = response.choices[0].message.content
            logger.info("synthesis_completed", length=len(state.final_answer))
        except Exception as e:
            logger.error("synthesis_failed", error=str(e))
            if not state.final_answer:
                state.final_answer = "Final answer synthesis failed after truncation."

    state.is_terminated = True
    state.ended_at = datetime.utcnow()
    return state
