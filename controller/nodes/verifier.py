"""
Verifier Node — executes selective self-validation logic.
"""
from __future__ import annotations
from controller.state import AgentState, ReasoningStep
from optimizer.modules.verifier import SelfValidationRuntime
from tracing.tracer import global_tracer
from tracing.schema import TraceEvent, EventClass
import structlog

logger = structlog.get_logger(__name__)

async def verifier_node(state: AgentState) -> AgentState:
    """
    Executes a verification pass if triggered by the arbitrator.
    """
    toggles = state.metadata.get("ablation_toggles", {})
    if not toggles.get("verification", True):
        return state

    if not state.metadata.get("verification_triggered"):
        return state
        
    logger.info("executing_verification", run_id=state.run_id)
    
    # Track verification attempts to prevent infinite correction loops
    verify_count = state.metadata.get("verification_attempts", 0)
    if verify_count >= 2:
        logger.warning("max_verification_attempts_reached", run_id=state.run_id)
        state.metadata["verification_triggered"] = False
        return state
    
    state.metadata["verification_attempts"] = verify_count + 1
    
    runtime = SelfValidationRuntime()
    outcome = await runtime.validate(state)
    
    from controller.utils import add_step, add_verification
    
    # Persist outcome
    state.verification_history.append(outcome.model_dump())
    
    # Emit Trace
    await global_tracer.emit(TraceEvent(
        experiment_id=state.experiment_id,
        run_id=state.experiment_id,
        question_id=state.question_id,
        event_class=EventClass.VERIFICATION_TRIGGER,
        event_type="self_validation",
        step=state.step_count,
        payload=outcome.model_dump(),
        node_id="verifier"
    ))
    
    add_verification(state, outcome.model_dump())
    
    if not outcome.is_valid:
        # Inject a critique step to guide the next reasoning iteration
        critique_step = ReasoningStep(
            step=state.step_count + 1,
            thought=f"[SELF-VALIDATION FAILURE] {outcome.critique}",
            action=None,
            observation="Self-correction triggered."
        )
        add_step(state, critique_step)
        logger.warning("verification_failed", run_id=state.run_id, critique=outcome.critique)
    else:
        logger.info("verification_passed", run_id=state.run_id)
        
    # Clear trigger to avoid infinite loops
    state.metadata["verification_triggered"] = False
    
    return state
