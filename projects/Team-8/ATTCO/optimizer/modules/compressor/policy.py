"""
Compression Policy Engine — decides how to optimize the active reasoning trace.
"""
from __future__ import annotations
from typing import List
from controller.state import AgentState
from infrastructure.config.profile_manager import ProfileManager
from .schema import TraceValueScore, CompressionDecision, CompressionStrategy

class CompressionPolicy:
    """Decides when and how to compress reasoning history."""
    
    def __init__(self, min_steps_to_compress: int | None = None, context_threshold: float | None = None):
        self.min_steps_to_compress = min_steps_to_compress if min_steps_to_compress is not None else ProfileManager.resolve_threshold("min_steps_to_compress", 3)
        self.context_threshold = context_threshold or ProfileManager.resolve_threshold("context_compression_ratio", 0.4)

    def evaluate(self, state: AgentState, scores: List[TraceValueScore]) -> CompressionDecision:
        """Produce a compression plan based on value scores."""
        
        # Use calibrated threshold
        threshold = state.calibration_context.get("context_threshold", self.context_threshold)
        
        # If trace is short, retain everything
        if len(scores) < self.min_steps_to_compress:
            return CompressionDecision(
                strategies=scores,
                original_token_estimate=len(scores) * 200, # Mock token count
                compressed_token_estimate=len(scores) * 200,
                compression_ratio=1.0,
                rationale="Trace length below compression threshold."
            )

        # Apply strategy overrides based on policy threshold
        final_strategies = []
        original_tokens = 0
        compressed_tokens = 0
        
        for score in scores:
            original_tokens += 200
            
            # If utility is below threshold and it's not critical, enforce drop
            if score.context_utility < threshold and not score.is_critical:
                score.compression_strategy = CompressionStrategy.DROP
                compressed_tokens += 0
            elif score.compression_strategy == CompressionStrategy.SUMMARIZE:
                compressed_tokens += 50
            else:
                compressed_tokens += 200
                
            final_strategies.append(score)
            
        ratio = compressed_tokens / max(1, original_tokens)
        
        return CompressionDecision(
            strategies=final_strategies,
            original_token_estimate=original_tokens,
            compressed_token_estimate=compressed_tokens,
            compression_ratio=ratio,
            rationale=f"Compressed trace to {ratio:.1%} of original size using selective retention."
        )
