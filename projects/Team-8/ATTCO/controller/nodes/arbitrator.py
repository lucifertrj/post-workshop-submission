"""
Arbitrator Node — central coordination point for all adaptive optimizations.
"""
from __future__ import annotations
from controller.state import AgentState, ToolCall
from optimizer.modules.arbitrator import ArbitrationEngine, OptimizerProposal, OptimizerAction
from optimizer.modules.depth_controller import DepthController
from optimizer.modules.confidence import ConfidenceExtractor, EarlyStoppingPolicy
from optimizer.modules.tool_governance import ToolNecessityExtractor, ToolGatingPolicy
from optimizer.modules.verifier import VerificationRiskEngine, VerificationPolicy

import structlog
logger = structlog.get_logger(__name__)

async def arbitrator_node(state: AgentState) -> AgentState:
    """
    Collects proposals from all optimizer layers and produces a unified decision.
    """
    logger.info("arbitrator_node_entry", step=state.step_count)
    if state.is_terminated:
        return state

    proposals = []
    toggles = state.metadata.get("ablation_toggles", {})

    # --- Hard Safety Guard: Arbitration Oscillation Detection ---
    if len(state.arbitration_history) > 20:
        logger.warning("arbitration_oscillation_detected", count=len(state.arbitration_history))
        state.is_terminated = True
        state.termination_cause = "safety_halt_oscillation"
        state.final_answer = "System halted to prevent infinite optimization loop. Synthesizing partial conclusion..."
        return state

    # --- Hard Safety Guard: Global Step Ceiling ---
    max_steps = toggles.get("max_steps", 15)
    if state.step_count >= max_steps:
        logger.warning("max_steps_reached", current=state.step_count, limit=max_steps)
        state.is_terminated = True
        state.termination_cause = "depth_ceiling_truncation"
        return state

    # 1. Depth Proposal
    if toggles.get("depth_controller", True):
        # Only check depth if we haven't already decided to stop
        depth_proposal = DepthController.propose(state)
        if depth_proposal:
            proposals.append(depth_proposal)

    # 2. Confidence Proposal
    if toggles.get("early_stopping", True):
        # Layered Gate: Confidence only matters if we have at least 2 steps
        if state.step_count >= 2:
            conf_extractor = ConfidenceExtractor()
            from optimizer.modules.confidence import EarlyStoppingPolicy
            conf_policy = EarlyStoppingPolicy(stop_threshold=toggles.get("stop_threshold", 0.85))
            conf_score = await conf_extractor.estimate(state)
            conf_proposal = conf_policy.propose(state, conf_score)
            if conf_proposal:
                proposals.append(conf_proposal)

    # 3. Verification Proposal (Selective Correctness Governance)
    if toggles.get("verification", True):
        # Layered Gate: Verification is expensive, only do it if confidence is mid-range or steps > 5
        if state.step_count > 5:
            risk_engine = VerificationRiskEngine()
            from optimizer.modules.verifier import VerificationPolicy
            verify_policy = VerificationPolicy(risk_threshold=toggles.get("verification_risk", 0.6))
            risk_score = await risk_engine.estimate_risk(state)
            verify_proposal = verify_policy.propose(state, risk_score)
            if verify_proposal:
                proposals.append(verify_proposal)

    # 4. Tool Proposal (if action exists)
    from controller.utils import get_last_step
    last_step = get_last_step(state)
    if toggles.get("tool_gating", True) and last_step and last_step.action and not last_step.action.lower().startswith("finish"):
        # Layered Gate: Tool gating only after Step 1
        if state.step_count >= 1:
            action_str = last_step.action
            tool_name = action_str.split("[")[0].strip()
            dummy_tc = ToolCall(tool_name=tool_name, tool_input={})
            
            tool_extractor = ToolNecessityExtractor()
            from optimizer.modules.tool_governance import ToolGatingPolicy
            tool_policy = ToolGatingPolicy(utility_threshold=toggles.get("utility_threshold", 0.5))
            tool_score = await tool_extractor.estimate(state, dummy_tc)
            tool_proposal = tool_policy.propose(state, tool_score)
            if tool_proposal:
                proposals.append(tool_proposal)

    # Arbitrate
    engine = ArbitrationEngine()
    decision = await engine.arbitrate(
        experiment_id=state.experiment_id,
        question_id=state.question_id,
        proposals=proposals,
        current_depth=state.step_count
    )

    # Persist decision
    state.arbitration_history.append(decision.model_dump())
    
    from controller.utils import add_intervention, get_last_step, update_last_step
    
    # --- Trajectory Persistence: Inject Intervention into Reasoning History ---
    if decision.final_action != OptimizerAction.CONTINUE:
        add_intervention(state, decision.final_action, decision.rationale, decision.winning_optimizer, state.step_count)

    # Enforce decision with finality
    if decision.final_action == OptimizerAction.TRUNCATE:
        state.is_terminated = True
        state.termination_cause = "arbitrated_truncation"
        state.final_answer = getattr(state, "final_answer", None) or f"ATTCO Truncation: {decision.rationale}"
        logger.info("intervention_applied", type="TRUNCATE", rationale=decision.rationale)
        
    elif decision.final_action == OptimizerAction.STOP:
        state.is_terminated = True
        state.termination_cause = "arbitrated_stop"
        if not state.final_answer or "Arbitrated" in state.final_answer:
            state.final_answer = f"ATTCO Early Stop: {decision.rationale}"
        logger.info("intervention_applied", type="EARLY_STOP", rationale=decision.rationale)
        
    elif decision.final_action == OptimizerAction.VERIFY:
        verify_count = len([d for d in state.arbitration_history if d.get("final_action") == OptimizerAction.VERIFY.value])
        if verify_count <= 2:
            state.metadata["verification_triggered"] = True
            state.metadata["verification_rationale"] = decision.rationale
            logger.info("intervention_applied", type="VERIFY", rationale=decision.rationale)
        else:
            state.is_terminated = True
            state.termination_cause = "verification_loop_halt"
        
    elif decision.final_action == OptimizerAction.SUPPRESS_TOOL:
        last_step = get_last_step(state)
        if last_step and last_step.action:
            tool_name = last_step.action.split("[")[0].strip()
            # Explicitly mark for UI
            observation = f"⚠️ [TOOL SUPPRESSED BY ATTCO] {decision.rationale}"
            update_last_step(state, observation=observation, action=None)
            state.metadata["tools_suppressed_count"] = state.metadata.get("tools_suppressed_count", 0) + 1
            logger.info("intervention_applied", type="TOOL_SUPPRESSION", tool=tool_name)

    # Emit Intervention Trace Event
    if decision.final_action != OptimizerAction.CONTINUE:
        from tracing.tracer import global_tracer
        from tracing.schema import TraceEvent, EventClass
        await global_tracer.emit(TraceEvent(
            experiment_id=state.experiment_id,
            run_id=state.experiment_id,
            question_id=state.question_id,
            event_class=EventClass.ARBITRATION_EVENT,
            event_type="intervention_triggered",
            step=state.step_count,
            payload={"action": decision.final_action, "rationale": decision.rationale},
            node_id="arbitrator"
        ))
            
    return state
