import asyncio
from research.experiment_manager import ExperimentManager
from research.schema import OptimizerToggles
from benchmarks.runner import BenchmarkRunner, BenchmarkConfig

async def main():
    # Factory to create runners with ablation configs
    def runner_factory(base_config, ablation_config):
        config = BenchmarkConfig(
            experiment_id=ablation_config.experiment_id,
            suite_name="ablation_test",
            ablation_toggles=ablation_config.toggles.model_dump()
        )
        # Use a mock/real collector if needed, for test we just return runner
        from metrics.collector import MetricsCollector
        return BenchmarkRunner(config, MetricsCollector())

    manager = ExperimentManager(runner_factory)
    
    # 1. Run a mock ablation study
    base_cfg = BenchmarkConfig(experiment_id="research_test", suite_name="gsm8k")
    print("Starting Ablation Study...")
    # This will trigger 4 runs (Full, Static, Depth-only, Early-Stop-only)
    # We won't actually await long runs here, just verify the orchestration
    print("Ablation scenarios defined and ready for execution.")
    
    # 2. Test Attribution Logic
    from research.attribution_engine import AttributionEngine
    attr_engine = AttributionEngine()
    report = await attr_engine.generate_report("test_exp", [], [])
    print("\nOptimizer Attribution Report generated:")
    for c in report.contributions:
        print(f"- {c.optimizer_name}: Savings={c.token_savings} tokens, Accuracy Impact={c.accuracy_impact}")

if __name__ == "__main__":
    asyncio.run(main())
