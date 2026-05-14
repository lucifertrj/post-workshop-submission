"""
Benchmark execution launcher with Hydra config composition.
Usage: python scripts/run_benchmark.py experiment=baseline benchmark=gsm8k
"""
from __future__ import annotations
from pathlib import Path
import hydra
import asyncio
from omegaconf import DictConfig, OmegaConf
import structlog
from experiments.registry import ExperimentRegistry
from attco_datasets.loader import get_loader
from benchmarks.runner import BenchmarkConfig, BenchmarkRunner

logger = structlog.get_logger(__name__)

@hydra.main(config_path="../configs", config_name="config", version_base="1.3")
def main(cfg: DictConfig) -> None:
    asyncio.run(async_main(cfg))

async def async_main(cfg: DictConfig) -> None:
    registry = ExperimentRegistry()
    record = registry.register(
        name=cfg.experiment.name,
        config=OmegaConf.to_container(cfg, resolve=True),  # type: ignore[arg-type]
    )
    logger.info(f"Experiment registered: {record.experiment_id} | Git SHA: {record.git_sha}")
    
    # Setup dataset
    dataset_name = cfg.get("benchmark", {}).get("name", "gsm8k")
    max_samples = cfg.get("benchmark", {}).get("max_samples", 5)
    
    logger.info("Loading dataset", dataset=dataset_name, max_samples=max_samples)
    loader = get_loader(dataset_name)
    questions = loader.load(split="test", max_samples=max_samples)
    
    from metrics.collector import MetricsCollector
    from metrics.store import MetricsStore
    from tracing.tracer import global_tracer
    from tracing.backends.local import LocalTracerBackend
    
    # Setup tracing
    trace_backend = LocalTracerBackend(registry.artifacts_dir / record.experiment_id / "traces")
    global_tracer._backends = [trace_backend]
    await global_tracer.start()
    
    # Setup metrics
    store = MetricsStore(db_path=Path(f"{registry.artifacts_dir}/metrics.duckdb"))
    collector = MetricsCollector(store=store)
    
    from infrastructure.config.profile_manager import ProfileManager
    ProfileManager.load(cfg.get("runtime_profile"))

    # Setup runner
    runner_cfg = BenchmarkConfig(
        experiment_id=record.experiment_id,
        suite_name=dataset_name,
        concurrency=cfg.get("infra", {}).get("concurrency", 4),
        runtime_profile=ProfileManager.get_active_profile_name()
    )
    runner = BenchmarkRunner(config=runner_cfg, metrics_collector=collector)
    
    logger.info("Starting benchmark runner...")
    summary = await runner.run(questions)
    
    await collector.close()
    
    from metrics.schema import RunSummary
    
    run_summary = RunSummary(
        run_id=record.experiment_id,
        experiment_id=record.experiment_id,
        total_questions=summary.total_questions,
        accuracy=summary.metrics["avg_accuracy"],
        latency_total_ms_mean=summary.metrics["avg_latency_ms"],
        latency_total_ms_p95=summary.metrics["avg_latency_ms"], # Placeholder p95
        tokens_input_mean=0.0,
        tokens_output_mean=0.0,
        step_count_mean=0.0,
        tool_call_count_mean=0.0,
        efficiency_ratio=0.0,
        runtime_profile=ProfileManager.get_active_profile_name()
    )
    store.write_summary(run_summary)
    store.export_parquet(f"{registry.artifacts_dir}/{record.experiment_id}/metric_events.parquet")
    store.close()
    await global_tracer.close()
    
    logger.info(
        "Benchmark complete",
        total_questions=summary.total_questions,
        failed=len(summary.failed_ids),
        accuracy=summary.metrics["avg_accuracy"],
        latency=summary.metrics["avg_latency_ms"],
        tokens=summary.metrics["avg_tokens"]
    )

if __name__ == "__main__":
    main()
