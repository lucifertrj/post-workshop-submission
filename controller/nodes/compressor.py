"""
Compressor Node — executes adaptive trace compression to optimize context.
"""
from __future__ import annotations
from controller.state import AgentState
from optimizer.modules.compressor import TraceValueEngine, CompressionPolicy, ContextOptimizerRuntime
from tracing.tracer import global_tracer
from tracing.schema import TraceEvent, EventClass
import structlog

logger = structlog.get_logger(__name__)

async def compressor_node(state: AgentState) -> AgentState:
    """
    Optimizes the active reasoning trace before the next reasoning step.
    """
    toggles = state.metadata.get("ablation_toggles", {})
    if not toggles.get("compression", True):
        return state

    if state.is_terminated or len(state.steps) < 3:
        return state
        
    logger.info("executing_trace_compression", run_id=state.run_id, step_count=len(state.steps))
    
    # Use aggressive threshold if early stopping is also aggressive
    threshold = toggles.get("context_threshold", 0.4)
    if toggles.get("early_stopping") and toggles.get("stop_threshold", 1.0) < 0.7:
        threshold = 0.2 # Extreme compression
        
    engine = TraceValueEngine()
    policy = CompressionPolicy(min_steps_to_compress=3, context_threshold=threshold)
    runtime = ContextOptimizerRuntime()
    
    # 1. Analyze Trace Value
    scores = await engine.analyze_trace(state)
    
    # 2. Decide Compression Plan
    decision = policy.evaluate(state, scores)
    
    if decision.compression_ratio < 0.95: # Only apply if meaningful savings
        # 3. Apply Optimization
        state = await runtime.optimize(state, decision)
        
        # 4. Emit Trace
        await global_tracer.emit(TraceEvent(
            experiment_id=state.experiment_id,
            run_id=state.experiment_id,
            question_id=state.question_id,
            event_class=EventClass.COMPRESSION_EVENT,
            event_type="trace_compression",
            step=state.step_count,
            payload=decision.model_dump(),
            node_id="compressor"
        ))
        
        logger.info("trace_compressed", 
                    run_id=state.run_id, 
                    ratio=f"{decision.compression_ratio:.1%}",
                    tokens_saved=decision.original_token_estimate - decision.compressed_token_estimate)
    
    return state
