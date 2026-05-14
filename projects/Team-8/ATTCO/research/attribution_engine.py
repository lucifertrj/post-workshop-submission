"""
Attribution Engine — calculates per-optimizer contributions to efficiency and correctness.
"""
from __future__ import annotations
from typing import List, Dict, Any
from .schema import AttributionReport, OptimizerContribution

class AttributionEngine:
    """Post-processor for experiment telemetry to attribute system performance."""
    
    async def generate_report(self, experiment_id: str, trace_events: List[Dict[str, Any]], metrics: List[Dict[str, Any]]) -> AttributionReport:
        """Analyze traces and metrics to attribute gains."""
        
        contributions = []
        optimizers = ["depth_controller", "confidence_runtime", "tool_governance", "compressor", "verifier"]
        
        # Aggregate interventions from traces
        intervention_counts = {opt: 0 for opt in optimizers}
        for event in trace_events:
            node_id = event.get("node_id", "")
            if node_id in intervention_counts:
                intervention_counts[node_id] += 1
                
        # Calculate contributions
        # In a real system, we'd compare against a baseline run. 
        # Here we estimate based on the intervention payloads.
        total_tokens_saved = 0
        total_latency_saved = 0
        
        for opt in optimizers:
            # Mock calculation for prototype
            tokens_saved = intervention_counts[opt] * 150 # Estimated
            latency_saved = intervention_counts[opt] * 200.0
            
            contributions.append(OptimizerContribution(
                optimizer_name=opt,
                token_savings=tokens_saved,
                latency_savings_ms=latency_saved,
                accuracy_impact=0.01 if opt != "verifier" else 0.05,
                verification_overhead_ms=150.0 if opt == "verifier" else 0.0,
                intervention_count=intervention_counts[opt]
            ))
            total_tokens_saved += tokens_saved
            total_latency_saved += latency_saved
            
        return AttributionReport(
            experiment_id=experiment_id,
            contributions=contributions,
            cumulative_token_reduction=total_tokens_saved,
            cumulative_latency_reduction=total_latency_saved,
            pareto_score=0.85 # Placeholder
        )
