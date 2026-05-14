"""Reason node — LLM thought generation step."""
from __future__ import annotations
import json
import time
from typing import Dict, Any, List
from controller.state import AgentState, ReasoningStep
from llm.wrapper import LLMWrapper
import structlog
logger = structlog.get_logger(__name__)

async def reason_node(state: AgentState) -> AgentState:
    """
    Generate the next ReAct thought via LLM.
    Uses LLMWrapper to call the model.
    """
    # Hard termination check
    max_steps = state.metadata.get("ablation_toggles", {}).get("max_steps", 15)
    if state.step_count >= max_steps:
        state.is_terminated = True
        state.termination_cause = "max_steps_exceeded"
        state.final_answer = "Error: Maximum reasoning steps exceeded without conclusion."
        return state

    # Assuming config is available via state.metadata or instantiated elsewhere
    # For now, we instantiate a default LLMWrapper if not injected
    llm = LLMWrapper(provider="openai", model_id="gpt-4o", temperature=0.0)
    
    logger.info("reason_node_entry", step=state.step_count)
    start_time = time.perf_counter()
    
    # Build prompt from state
    messages = [{"role": "system", "content": "You are a ReAct agent. Think step by step and optionally return a tool call."}]
    messages.append({"role": "user", "content": state.question})
    
    from controller.utils import add_step, get_steps
    
    # --- Causal Optimization: Use Compressed History if available ---
    history_source = state.metadata.get("optimized_steps")
    if history_source:
        logger.info("using_compressed_history", steps=len(history_source))
        steps_to_render = [ReasoningStep.model_validate(s) if isinstance(s, dict) else s for s in history_source]
    else:
        steps_to_render = get_steps(state)

    for step in steps_to_render:
        messages.append({"role": "assistant", "content": step.thought})
        if step.action:
             messages.append({"role": "assistant", "content": f"Action: {step.action}"})
        if step.observation:
             messages.append({"role": "user", "content": f"Observation: {step.observation}"})

    response = await llm.agenerate(messages)
    content = response.choices[0].message.content or ""
    
    usage = response.usage
    tokens_used = (usage.prompt_tokens + usage.completion_tokens) if usage else 0
    latency_ms = (time.perf_counter() - start_time) * 1000
    
    # Parse action if any
    action = None
    if "Action:" in content:
        parts = content.split("Action:")
        thought = parts[0].strip()
        action = parts[1].split("\n")[0].strip()
    elif "Final Answer:" in content:
        state.is_terminated = True
        parts = content.split("Final Answer:")
        thought = parts[0].strip()
        state.final_answer = parts[1].strip()
    else:
        thought = content.strip()
    
    new_step = ReasoningStep(
        step=state.step_count + 1,
        thought=thought,
        action=action,
        tokens_used=tokens_used,
        latency_ms=latency_ms
    )
    
    add_step(state, new_step)
    state.total_tokens += tokens_used
    state.total_latency_ms += latency_ms
    
    from tracing.tracer import global_tracer
    from tracing.schema import TraceEvent, EventClass
    
    await global_tracer.emit(TraceEvent(
        experiment_id=state.experiment_id,
        run_id=state.experiment_id, # Simplified run_id for now
        question_id=state.question_id,
        event_class=EventClass.REASONING_STEP,
        event_type="reason_generated",
        step=state.step_count,
        payload={"thought": thought, "action": action},
        token_delta=tokens_used,
        latency_ms=latency_ms,
        node_id="reason"
    ))
    
    logger.info("reason_node_exit", step=state.step_count, terminated=state.is_terminated)
    return state
