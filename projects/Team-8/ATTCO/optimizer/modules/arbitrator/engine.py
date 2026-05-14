"""
Arbitration Engine — resolves conflicts between multiple adaptive optimizers.
"""
from __future__ import annotations
import time
from typing import List, Dict, Any
from .schema import OptimizerProposal, OptimizerAction, ArbitrationDecision
from tracing.tracer import global_tracer
from tracing.schema import TraceEvent, EventClass

class ArbitrationEngine:
    """
    Central brain for coordinating adaptive inference policies.
    Enforces a strict priority hierarchy for conflict resolution.
    """
    
    # Priority: TRUNCATE > STOP > SUPPRESS_TOOL > CONTINUE
    PRIORITY_MAP = {
        OptimizerAction.TRUNCATE: 100,
        OptimizerAction.STOP: 80,
        OptimizerAction.VERIFY: 70,
        OptimizerAction.SUPPRESS_TOOL: 50,
        OptimizerAction.CONTINUE: 0
    }

    async def arbitrate(
        self, 
        experiment_id: str,
        question_id: str,
        proposals: List[OptimizerProposal],
        current_depth: int = 0
    ) -> ArbitrationDecision:
        start_time = time.perf_counter()
        
        if not proposals:
            return ArbitrationDecision(
                final_action=OptimizerAction.CONTINUE,
                winning_optimizer="default",
                overridden_proposals=[],
                rationale="No proposals received. Defaulting to continue.",
                arbitration_latency_ms=(time.perf_counter() - start_time) * 1000
            )

        # Enforce Minimum Reasoning Guard at Arbitration Level
        from infrastructure.config.profile_manager import ProfileManager
        min_depth = ProfileManager.resolve_threshold("min_reasoning_before_truncation", 3)
        
        # If below min depth, filter out termination proposals
        if current_depth < min_depth:
            filtered_proposals = []
            for p in proposals:
                if p.action in [OptimizerAction.TRUNCATE, OptimizerAction.STOP]:
                    p.reason = f"INTERCEPTED: {p.reason} (Minimum depth {min_depth} not reached)"
                    p.action = OptimizerAction.CONTINUE
                    p.confidence = 0.0
                filtered_proposals.append(p)
            proposals = filtered_proposals

        # Emit proposals to telemetry
        for p in proposals:
            await global_tracer.emit(TraceEvent(
                experiment_id=experiment_id,
                run_id=experiment_id,
                question_id=question_id,
                event_class=EventClass.OPTIMIZER_PROPOSAL,
                event_type="proposal",
                payload=p.model_dump(),
                node_id=p.optimizer_name
            ))

        # Sort by priority and then confidence
        sorted_proposals = sorted(
            proposals, 
            key=lambda x: (self.PRIORITY_MAP.get(x.action, 0), x.confidence),
            reverse=True
        )

        winner = sorted_proposals[0]
        overridden = sorted_proposals[1:]
        
        latency = (time.perf_counter() - start_time) * 1000
        
        decision = ArbitrationDecision(
            final_action=winner.action,
            winning_optimizer=winner.optimizer_name,
            overridden_proposals=overridden,
            rationale=f"Winner selected by priority ({winner.action}) and confidence ({winner.confidence:.2f}). Reason: {winner.reason}",
            arbitration_latency_ms=latency
        )

        # Emit arbitration decision
        await global_tracer.emit(TraceEvent(
            experiment_id=experiment_id,
            run_id=experiment_id,
            question_id=question_id,
            event_class=EventClass.ARBITRATION_DECISION,
            event_type="arbitration",
            payload=decision.model_dump(),
            node_id="arbitrator"
        ))

        return decision
