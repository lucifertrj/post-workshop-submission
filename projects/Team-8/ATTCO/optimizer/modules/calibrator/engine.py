"""
Calibration Engine — analyzes telemetry trends to adapt optimization policies.
"""
from __future__ import annotations
from typing import List, Dict, Any
from .schema import CalibrationDecision, ParameterCategory

class CalibrationEngine:
    """Analyzes performance metrics to calculate parameter shifts."""
    
    def calculate_adjustment(
        self, 
        current_params: Dict[str, float],
        metrics_history: List[Dict[str, Any]]
    ) -> CalibrationDecision:
        """Analyze accuracy vs cost trends to compute threshold updates."""
        
        # Heuristic: if accuracy is low (< 0.7) and cost is low, 
        # decrease confidence/verification thresholds to allow more reasoning.
        # If accuracy is high (> 0.9) and cost is high, 
        # increase thresholds to be more aggressive with optimization.
        
        avg_accuracy = sum(m.get("accuracy", 0.0) for m in metrics_history) / max(1, len(metrics_history))
        avg_cost = sum(m.get("total_tokens", 0) for m in metrics_history) / max(1, len(metrics_history))
        
        updates = {}
        rationale = "Stable state; no calibration required."
        
        if avg_accuracy < 0.7:
            updates["stop_threshold"] = -0.05 # Lower threshold = more reasoning
            updates["verification_threshold"] = -0.1
            rationale = f"Low accuracy ({avg_accuracy:.2f}) detected. Loosening optimization constraints."
        elif avg_accuracy > 0.9 and avg_cost > 1000:
            updates["stop_threshold"] = 0.05 # Higher threshold = more aggressive stopping
            updates["utility_threshold"] = 0.05 # More tool suppression
            rationale = f"High accuracy ({avg_accuracy:.2f}) and high cost detected. Increasing optimization aggressiveness."
            
        return CalibrationDecision(
            parameter_updates=updates,
            rationale=rationale,
            metrics_baseline={"avg_accuracy": avg_accuracy, "avg_cost": avg_cost}
        )
