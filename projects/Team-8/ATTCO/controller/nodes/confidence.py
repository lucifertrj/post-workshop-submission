"""
Confidence Node — Estimates reasoning confidence and makes early stop decisions.
"""
from __future__ import annotations
from controller.state import AgentState
from optimizer.modules.confidence import ConfidenceExtractor, EarlyStoppingPolicy
from tracing.tracer import global_tracer
from tracing.schema import TraceEvent, EventClass
import structlog

logger = structlog.get_logger(__name__)

async def confidence_node(state: AgentState) -> AgentState:
    """
    Evaluate reasoning confidence and conditionally stop early.
    """
    if state.is_terminated:
        return state
        
    extractor = ConfidenceExtractor()
    policy = EarlyStoppingPolicy(stop_threshold=0.85, min_steps=2)
    
    # Estimate Confidence
    score = await extractor.estimate(state)
    
    # Evaluate Stop Policy
    decision = policy.evaluate(state, score)
    
    # Enrich State
    state.metadata.setdefault("confidence_trajectory", []).append(score.model_dump())
    
    # Emit Trace
    await global_tracer.emit(TraceEvent(
        experiment_id=state.experiment_id,
        run_id=state.experiment_id,
        question_id=state.question_id,
        event_class=EventClass.CONFIDENCE_ESTIMATE,
        event_type="confidence_evaluation",
        step=state.step_count,
        payload={
            "score": score.model_dump(),
            "decision": decision.model_dump()
        },
        node_id="confidence"
    ))
    
    if decision.should_stop:
        logger.info("early_stop_triggered", run_id=state.run_id, reason=decision.reason)
        state.is_terminated = True
        state.termination_cause = "confidence_early_stop"
        state.final_answer = "Execution terminated early due to high confidence / looping."
        
        # Emit early stop specifically
        await global_tracer.emit(TraceEvent(
            experiment_id=state.experiment_id,
            run_id=state.experiment_id,
            question_id=state.question_id,
            event_class=EventClass.TERMINATION_EVENT,
            event_type="early_stop",
            step=state.step_count,
            payload=decision.model_dump(),
            node_id="confidence"
        ))
        
    return state
