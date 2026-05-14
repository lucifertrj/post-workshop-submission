"""
Tool Gater Node — evaluates if an action should be allowed to execute.
"""
from __future__ import annotations
import json
from controller.state import AgentState, ToolCall
from optimizer.modules.tool_governance import ToolNecessityExtractor, ToolGatingPolicy
from tracing.tracer import global_tracer
from tracing.schema import TraceEvent, EventClass
import structlog

logger = structlog.get_logger(__name__)

async def tool_gater_node(state: AgentState) -> AgentState:
    """
    Conditionally suppress tools before they hit act_node.
    """
    if state.is_terminated or not state.steps:
        return state
        
    last_step = state.steps[-1]
    if not last_step.action or last_step.action.lower().startswith("finish"):
        return state
        
    action_str = last_step.action
    tool_name = action_str.split("[")[0].strip()
    
    # We create a dummy ToolCall to pass to the extractor
    dummy_tc = ToolCall(tool_name=tool_name, tool_input={})
    
    extractor = ToolNecessityExtractor()
    policy = ToolGatingPolicy(utility_threshold=0.3, max_cost=1000)
    
    score = await extractor.estimate(state, dummy_tc)
    decision = policy.evaluate(state, score)
    
    # Record metadata
    state.metadata.setdefault("tool_necessity_trajectory", []).append(score.model_dump())
    
    # Emit Trace
    await global_tracer.emit(TraceEvent(
        experiment_id=state.experiment_id,
        run_id=state.experiment_id,
        question_id=state.question_id,
        event_class=EventClass.TOOL_GATE_DECISION,
        event_type="tool_gating",
        step=state.step_count,
        payload={
            "score": score.model_dump(),
            "decision": decision.model_dump()
        },
        node_id="tool_gater"
    ))
    
    if decision.should_suppress:
        logger.info("tool_suppressed", run_id=state.run_id, tool=tool_name, reason=decision.reason)
        # Suppress it: create the failed ToolCall ourselves and clear the action so act_node skips it
        suppressed_tc = ToolCall(
            tool_name=tool_name, 
            tool_input={"suppressed": True},
            error=f"Tool suppressed by adaptive governance: {decision.reason}",
            latency_ms=0.0
        )
        last_step.tool_calls.append(suppressed_tc)
        last_step.action = None # Act node will skip
        
        # Track suppression metrics count in metadata to easily pull in runner
        suppressed_count = state.metadata.get("tools_suppressed_count", 0)
        state.metadata["tools_suppressed_count"] = suppressed_count + 1
        
        latency_saved = state.metadata.get("tool_latency_saved_ms", 0.0)
        state.metadata["tool_latency_saved_ms"] = latency_saved + score.expected_latency_ms
        
    return state
