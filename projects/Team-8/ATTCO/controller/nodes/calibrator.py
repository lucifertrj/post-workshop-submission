"""
Calibrator Node — injects and adapts policy parameters into the execution lifecycle.
"""
from __future__ import annotations
from controller.state import AgentState
from optimizer.modules.calibrator import CalibrationManager, CalibrationEngine
from tracing.tracer import global_tracer
from tracing.schema import TraceEvent, EventClass
import structlog

logger = structlog.get_logger(__name__)

# Single global manager for the runtime instance (in production this would be persisted to DB)
global_calibration_manager = CalibrationManager()

async def calibrator_node(state: AgentState) -> AgentState:
    """
    Injects active policy parameters into the state for adaptive downstream use.
    """
    params = global_calibration_manager.get_current_parameters()
    state.calibration_context.update(params)
    
    # Emit Trace for parameter injection
    await global_tracer.emit(TraceEvent(
        experiment_id=state.experiment_id,
        run_id=state.experiment_id,
        question_id=state.question_id,
        event_class=EventClass.CALIBRATION_EVENT,
        event_type="parameter_injection",
        step=state.step_count,
        payload={"active_parameters": params},
        node_id="calibrator"
    ))
    
    return state
