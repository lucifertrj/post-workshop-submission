"""
Allocator Node — Assigns compute budget based on estimated difficulty.
"""
from __future__ import annotations
from controller.state import AgentState
import structlog
logger = structlog.get_logger(__name__)
from intelligence.allocator import default_policy_registry
from intelligence.difficulty.schema import DifficultyPrediction
from tracing.tracer import global_tracer
from tracing.schema import TraceEvent, EventClass

async def allocator_node(state: AgentState) -> AgentState:
    """
    Predict compute budget and enrich state metadata.
    Does not enforce constraints, just sets the runtime parameters.
    """
    diff_data = state.metadata.get("difficulty_prediction")
    if not diff_data:
        return state
        
    difficulty = DifficultyPrediction.model_validate(diff_data)
    
    policy = default_policy_registry.get_policy("heuristic_allocator")
    if not policy:
        return state
        
    allocation = await policy.allocate(difficulty)
    
    # Enrich state metadata
    state.metadata["compute_allocation"] = allocation.model_dump()
    
    # Emit Trace
    await global_tracer.emit(TraceEvent(
        experiment_id=state.experiment_id,
        run_id=state.experiment_id,
        question_id=state.question_id,
        event_class=EventClass.BUDGET_ALLOCATION,
        event_type="compute_allocation",
        step=0,
        payload=allocation.model_dump(),
        latency_ms=allocation.allocation_latency_ms,
        node_id="allocator"
    ))
    
    return state
