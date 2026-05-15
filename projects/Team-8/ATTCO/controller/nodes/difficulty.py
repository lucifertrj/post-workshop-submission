"""
Difficulty Node — Estimates query difficulty before reasoning.
"""
from __future__ import annotations
from controller.state import AgentState
import structlog
logger = structlog.get_logger(__name__)
from intelligence.difficulty import default_estimator_registry
from tracing.tracer import global_tracer
from tracing.schema import TraceEvent, EventClass

async def difficulty_node(state: AgentState) -> AgentState:
    """
    Predict query difficulty and enrich state metadata.
    Does not alter execution paths, just adds intelligence.
    """
    estimator = default_estimator_registry.get_estimator("heuristic_estimator")
    if not estimator:
        return state
        
    prediction = await estimator.estimate(state.question)
    
    # Enrich state metadata
    state.metadata["difficulty_prediction"] = prediction.model_dump()
    
    # Emit Trace
    await global_tracer.emit(TraceEvent(
        experiment_id=state.experiment_id,
        run_id=state.experiment_id,
        question_id=state.question_id,
        event_class=EventClass.DIFFICULTY_PREDICTION,
        event_type="difficulty_estimation",
        step=0,
        payload=prediction.model_dump(),
        latency_ms=prediction.latency_ms,
        node_id="difficulty"
    ))
    
    return state
