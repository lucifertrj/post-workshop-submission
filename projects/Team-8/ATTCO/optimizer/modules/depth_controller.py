"""
Adaptive Reasoning Depth Controller.
Enforces compute ceilings dynamically during graph execution.
"""
from __future__ import annotations
from typing import Optional
from controller.state import AgentState
from infrastructure.config.profile_manager import ProfileManager
from intelligence.allocator.schema import ComputeBudgetAllocation
from tracing.tracer import global_tracer
from tracing.schema import TraceEvent, EventClass
import structlog

logger = structlog.get_logger(__name__)

class DepthController:
    """Enforces compute allocation ceilings on the reasoning state."""
    
    @staticmethod
    async def enforce(state: AgentState) -> AgentState:
        # If already terminated, do nothing
        if state.is_terminated:
            return state
            
        allocation_data = state.metadata.get("compute_allocation")
        if not allocation_data:
            return state
            
        allocation = ComputeBudgetAllocation.model_validate(allocation_data)
        max_depth = allocation.max_reasoning_depth
        
        # Override with profile-specific limit if applicable
        profile_depth = ProfileManager.resolve_threshold("max_reasoning_depth", 15)
        max_depth = min(max_depth, profile_depth)

        # 1. Enforce Minimum Reasoning Depth
        min_depth = ProfileManager.resolve_threshold("min_reasoning_before_truncation", 3)
        if state.step_count < min_depth:
            return state

        # 2. Soft Warning Emission
        if state.step_count == max_depth - 1:
            logger.info("depth_ceiling_imminent", run_id=state.run_id, current=state.step_count, max=max_depth)
            await global_tracer.emit(TraceEvent(
                experiment_id=state.experiment_id,
                run_id=state.experiment_id,
                question_id=state.question_id,
                event_class=EventClass.ARBITRATION_EVENT,
                event_type="depth_warning",
                step=state.step_count,
                payload={"message": "⚠️ Depth budget nearing ceiling. Truncation imminent."},
                node_id="depth_controller"
            ))

        if state.step_count >= max_depth:
            # Ceiling reached! Truncate graph execution.
            state.is_terminated = True
            state.termination_cause = "depth_ceiling_truncation"
            state.final_answer = "Execution truncated: reasoning depth ceiling reached."
            
            logger.warning("graph_truncated", run_id=state.run_id, depth=state.step_count, max_depth=max_depth)
            
            # Emit truncation telemetry
            await global_tracer.emit(TraceEvent(
                experiment_id=state.experiment_id,
                run_id=state.experiment_id,
                question_id=state.question_id,
                event_class=EventClass.TRUNCATION_EVENT,
                event_type="depth_ceiling_reached",
                step=state.step_count,
                payload={
                    "max_depth_allocated": max_depth,
                    "actual_depth_reached": state.step_count,
                    "budget_class": allocation.budget_class.value
                },
                node_id="depth_controller"
            ))
            
        return state

    @staticmethod
    def propose(state: AgentState) -> Optional[OptimizerProposal]:
        from optimizer.modules.arbitrator.schema import OptimizerProposal, OptimizerAction
        
        allocation_data = state.metadata.get("compute_allocation")
        if not allocation_data:
            return None
            
        allocation = ComputeBudgetAllocation.model_validate(allocation_data)
        max_depth = allocation.max_reasoning_depth
        
        # Override with profile-specific limit
        profile_depth = ProfileManager.resolve_threshold("max_reasoning_depth", 15)
        max_depth = min(max_depth, profile_depth)

        # Honor Minimum Reasoning Depth
        min_depth = ProfileManager.resolve_threshold("min_reasoning_before_truncation", 3)
        if state.step_count < min_depth:
            return None
        
        if state.step_count >= max_depth:
            return OptimizerProposal(
                optimizer_name="depth_controller",
                action=OptimizerAction.TRUNCATE,
                confidence=1.0,
                reason=f"Depth ceiling ({max_depth}) reached.",
                metadata={"max_depth": max_depth, "actual_depth": state.step_count}
            )
        return None
