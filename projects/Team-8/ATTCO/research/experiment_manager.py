"""
Experiment Manager — orchestrates ablation studies, parameter sweeps, and scientific benchmarks.
"""
from __future__ import annotations
import asyncio
from typing import List, Dict, Any, Optional
from .schema import AblationConfig, OptimizerToggles, ExperimentSweep
from benchmarks.runner import BenchmarkRunner, BenchmarkConfig
import structlog

logger = structlog.get_logger(__name__)

class ExperimentManager:
    """Central orchestration for research-grade experimentation."""
    
    def __init__(self, runner_factory):
        self._runner_factory = runner_factory
        self._experiments: Dict[str, AblationConfig] = {}

    async def run_ablation_study(self, base_config: BenchmarkConfig) -> Dict[str, Any]:
        """Run a standard ablation suite (Full vs No-Optimizers vs One-by-One)."""
        logger.info("starting_ablation_study", suite=base_config.suite_name)
        
        scenarios = {
            "full_adaptive": OptimizerToggles(),
            "static_baseline": OptimizerToggles(
                depth_controller=False, early_stopping=False, tool_gating=False, 
                compression=False, verification=False, arbitration=False
            ),
            "only_depth": OptimizerToggles(early_stopping=False, tool_gating=False, compression=False, verification=False),
            "only_early_stop": OptimizerToggles(depth_controller=False, tool_gating=False, compression=False, verification=False),
        }
        
        results = {}
        for name, toggles in scenarios.items():
            exp_id = f"{base_config.experiment_id}_{name}"
            config = AblationConfig(experiment_id=exp_id, description=f"Ablation: {name}", toggles=toggles)
            
            # Run benchmark with specific ablation config
            runner = self._runner_factory(base_config, config)
            results[name] = await runner.run()
            
        return results

    async def run_parameter_sweep(self, sweep: ExperimentSweep) -> List[Dict[str, Any]]:
        """Execute a range-based sweep over a specific policy parameter."""
        logger.info("starting_parameter_sweep", param=sweep.parameter_name, values=sweep.values)
        
        results = []
        for val in sweep.values:
            # Deep copy and override
            current_config = sweep.base_config.model_copy(deep=True)
            current_config.overrides[sweep.parameter_name] = val
            current_config.experiment_id = f"{sweep.sweep_id}_{val}"
            
            runner = self._runner_factory(None, current_config) # Simplified for prototype
            results.append(await runner.run())
            
        return results
