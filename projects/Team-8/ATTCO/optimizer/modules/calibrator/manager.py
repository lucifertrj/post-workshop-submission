"""
Calibration Manager — manages versioned policy snapshots and parameter persistence.
"""
from __future__ import annotations
import uuid
from typing import Dict, List, Any, Optional
from .schema import PolicySnapshot, PolicyParameter, ParameterCategory, CalibrationDecision

class CalibrationManager:
    """Handles persistence and lifecycle of adaptive policy versions."""
    
    def __init__(self):
        # Initial default snapshot
        self._current_snapshot = self._create_default_snapshot()
        self._history: List[PolicySnapshot] = [self._current_snapshot]

    def _create_default_snapshot(self) -> PolicySnapshot:
        params = [
            PolicyParameter(name="stop_threshold", category=ParameterCategory.CONFIDENCE, current_value=0.85, default_value=0.85, min_value=0.5, max_value=0.99, description="Threshold for confidence-based early stopping."),
            PolicyParameter(name="verification_threshold", category=ParameterCategory.VERIFICATION, current_value=0.5, default_value=0.5, min_value=0.1, max_value=0.9, description="Threshold for triggering selective verification."),
            PolicyParameter(name="utility_threshold", category=ParameterCategory.TOOL_GATING, current_value=0.3, default_value=0.3, min_value=0.0, max_value=0.8, description="Utility floor for tool invocation gating."),
            PolicyParameter(name="context_threshold", category=ParameterCategory.COMPRESSION, current_value=0.4, default_value=0.4, min_value=0.1, max_value=0.9, description="Threshold for dropping low-value trace segments.")
        ]
        return PolicySnapshot(version_id=str(uuid.uuid4())[:8], parameters=params)

    def get_current_parameters(self) -> Dict[str, float]:
        return {p.name: p.current_value for p in self._current_snapshot.parameters}

    def apply_calibration(self, decision: CalibrationDecision) -> PolicySnapshot:
        """Create a new versioned snapshot with adjusted parameters."""
        new_params = []
        for p in self._current_snapshot.parameters:
            update_delta = decision.parameter_updates.get(p.name, 0.0)
            new_val = max(p.min_value, min(p.max_value, p.current_value + update_delta))
            
            new_params.append(PolicyParameter(
                **p.model_dump(exclude={"current_value"}),
                current_value=new_val
            ))
            
        new_snapshot = PolicySnapshot(
            version_id=str(uuid.uuid4())[:8],
            parameters=new_params,
            parent_version_id=self._current_snapshot.version_id,
            metadata={"rationale": decision.rationale}
        )
        
        self._current_snapshot = new_snapshot
        self._history.append(new_snapshot)
        return new_snapshot

    def rollback(self) -> Optional[PolicySnapshot]:
        """Revert to the previous versioned snapshot."""
        if len(self._history) > 1:
            self._history.pop()
            self._current_snapshot = self._history[-1]
            return self._current_snapshot
        return None

# Global singleton instance
global_calibration_manager = CalibrationManager()
