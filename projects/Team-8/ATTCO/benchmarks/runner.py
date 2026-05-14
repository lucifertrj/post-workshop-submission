"""
Benchmark Runner — async orchestration engine for benchmark suite execution.
Coordinates dataset loading, agent evaluation, and metrics collection.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import structlog

from metrics.collector import MetricsCollector, MetricEvent
from optimizer.modules.calibrator import global_calibration_manager, CalibrationEngine

logger = structlog.get_logger(__name__)


@dataclass
class BenchmarkConfig:
    experiment_id: str
    suite_name: str
    concurrency: int = 4
    max_questions: int | None = None
    random_seed: int = 42
    runtime_profile: str | None = None
    ablation_toggles: dict[str, bool] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    experiment_id: str
    suite_name: str
    total_questions: int
    completed: int
    failed: int
    failed_ids: list[str] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


class BenchmarkRunner:
    """
    Async benchmark runner. Evaluates questions concurrently up to
    the configured concurrency limit. All results are stored via
    MetricsCollector.
    """

    def __init__(
        self,
        config: BenchmarkConfig,
        metrics_collector: MetricsCollector,
    ) -> None:
        self._config = config
        self._metrics = metrics_collector

    async def run(self, questions: list[dict[str, Any]]) -> BenchmarkResult:
        from infrastructure.config.profile_manager import ProfileManager
        
        # Lock runtime profile for this experiment
        ProfileManager.load(self._config.runtime_profile)
        
        if self._config.max_questions:
            questions = questions[: self._config.max_questions]

        await self._metrics.start()

        semaphore = asyncio.Semaphore(self._config.concurrency)
        tasks = [self._evaluate_with_limit(semaphore, q) for q in questions]

        logger.info(
            "benchmark_started",
            experiment=self._config.experiment_id,
            suite=self._config.suite_name,
            total=len(questions),
        )

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        completed = [r for r in raw_results if not isinstance(r, Exception)]
        failed_exceptions = [r for r in raw_results if isinstance(r, Exception)]
        
        # We don't have question_ids for failures directly if they failed completely
        # but we can just count them.
        
        if completed:
            accuracy_mean = sum(r.get("accuracy", 0.0) for r in completed) / len(completed)
            latency_mean = sum(r.get("total_latency_ms", 0.0) for r in completed) / len(completed)
            tokens_mean = sum(r.get("total_tokens", 0) for r in completed) / len(completed)
        else:
            accuracy_mean = latency_mean = tokens_mean = 0.0

        metrics = {
            "avg_accuracy": accuracy_mean,
            "avg_latency_ms": latency_mean,
            "avg_tokens": tokens_mean,
        }

        for exc in failed_exceptions:
            logger.error("question_evaluation_failed", error=str(exc))

        logger.info(
            "benchmark_completed",
            completed=len(completed),
            failed=len(failed_exceptions),
        )

        await self._run_calibration(completed)

        return BenchmarkResult(
            experiment_id=self._config.experiment_id,
            suite_name=self._config.suite_name,
            total_questions=len(questions),
            completed=len(completed),
            failed=len(failed_exceptions),
            results=completed,  # type: ignore[arg-type]
            metrics=metrics
        )

    async def _evaluate_with_limit(
        self,
        semaphore: asyncio.Semaphore,
        question: dict[str, Any],
    ) -> dict[str, Any]:
        async with semaphore:
            return await self._evaluate_question(question)

    async def _evaluate_question(
        self, question: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Evaluate a question using the baseline agent (or future optimized agents).
        """
        from baseline.agent import BaselineAgent
        from benchmarks.harness import evaluate_prediction
        import time
        
        question_id = question.get("id", str(time.time()))
        question_text = question.get("question", str(question))
        dataset_name = question.get("dataset", "unknown")
        ground_truth = question.get("answer", "")
        
        agent = BaselineAgent(
            experiment_id=self._config.experiment_id,
            max_steps=10,
            ablation_toggles=self._config.ablation_toggles
        )
        
        result_state = await agent.run(question_id, question_text)
        
        scores = evaluate_prediction(
            prediction=result_state.get("final_answer", ""),
            ground_truth=ground_truth,
            dataset_name=dataset_name
        )
        
        from metrics.schema import MetricEvent
        import uuid
        
        # Emit metrics
        await self._metrics.record(MetricEvent(
            experiment_id=self._config.experiment_id,
            run_id=self._config.experiment_id,
            question_id=question_id,
            metric_name="avg_accuracy",
            value=scores.get("accuracy", 0.0),
            unit="pct"
        ))
        await self._metrics.record(MetricEvent(
            experiment_id=self._config.experiment_id,
            run_id=self._config.experiment_id,
            question_id=question_id,
            metric_name="avg_tokens",
            value=result_state.get("total_tokens", 0),
            unit="count"
        ))
        await self._metrics.record(MetricEvent(
            experiment_id=self._config.experiment_id,
            run_id=self._config.experiment_id,
            question_id=question_id,
            metric_name="avg_latency_ms",
            value=result_state.get("total_latency_ms", 0.0),
            unit="ms"
        ))
        
        await self._metrics.record(MetricEvent(
            experiment_id=self._config.experiment_id,
            run_id=self._config.experiment_id,
            question_id=question_id,
            metric_name="avg_cost",
            value=result_state.get("total_cost", 0.0),
            unit="usd"
        ))
        
        await self._metrics.record(MetricEvent(
            experiment_id=self._config.experiment_id,
            run_id=self._config.experiment_id,
            question_id=question_id,
            metric_name="avg_reasoning_depth",
            value=len(result_state.get("steps", [])),
            unit="count"
        ))
        
        diff_pred = result_state.get("metadata", {}).get("difficulty_prediction")
        if diff_pred:
            await self._metrics.record(MetricEvent(
                experiment_id=self._config.experiment_id,
                run_id=self._config.experiment_id,
                question_id=question_id,
                metric_name="predicted_expected_depth",
                value=diff_pred.get("expected_reasoning_depth", 0),
                unit="steps",
                tags={"difficulty_class": diff_pred.get("difficulty_class", "unknown")}
            ))
            await self._metrics.record(MetricEvent(
                experiment_id=self._config.experiment_id,
                run_id=self._config.experiment_id,
                question_id=question_id,
                metric_name="predicted_expected_compute",
                value=diff_pred.get("expected_compute_tokens", 0),
                unit="tokens",
                tags={"difficulty_class": diff_pred.get("difficulty_class", "unknown")}
            ))
            
        alloc_pred = result_state.metadata.get("compute_allocation")
        if alloc_pred:
            max_depth = alloc_pred.get("max_reasoning_depth", 0)
            await self._metrics.record(MetricEvent(
                experiment_id=self._config.experiment_id,
                run_id=self._config.experiment_id,
                question_id=question_id,
                metric_name="allocated_max_depth",
                value=max_depth,
                unit="steps",
                tags={"budget_class": alloc_pred.get("budget_class", "unknown")}
            ))
            await self._metrics.record(MetricEvent(
                experiment_id=self._config.experiment_id,
                run_id=self._config.experiment_id,
                question_id=question_id,
                metric_name="allocated_soft_budget",
                value=alloc_pred.get("soft_reasoning_budget", 0),
                unit="steps",
                tags={"budget_class": alloc_pred.get("budget_class", "unknown")}
            ))
            await self._metrics.record(MetricEvent(
                experiment_id=self._config.experiment_id,
                run_id=self._config.experiment_id,
                question_id=question_id,
                metric_name="allocated_token_budget",
                value=alloc_pred.get("expected_token_budget", 0),
                unit="tokens",
                tags={"budget_class": alloc_pred.get("budget_class", "unknown")}
            ))
            
            # Optimization Metrics
            actual_depth = len(result_state.steps)
            is_truncated = 1 if result_state.termination_cause == "depth_ceiling_truncation" else 0
            depth_saved = max(0, max_depth - actual_depth)
            utilization_ratio = actual_depth / max(1, max_depth)
            
            await self._metrics.record(MetricEvent(
                experiment_id=self._config.experiment_id,
                run_id=self._config.experiment_id,
                question_id=question_id,
                metric_name="truncation_rate",
                value=is_truncated,
                unit="count"
            ))
            await self._metrics.record(MetricEvent(
                experiment_id=self._config.experiment_id,
                run_id=self._config.experiment_id,
                question_id=question_id,
                metric_name="avg_depth_saved",
                value=depth_saved,
                unit="steps"
            ))
            await self._metrics.record(MetricEvent(
                experiment_id=self._config.experiment_id,
                run_id=self._config.experiment_id,
                question_id=question_id,
                metric_name="reasoning_utilization_ratio",
                value=utilization_ratio,
                unit="pct"
            ))
            
            # Confidence & Early Stop Metrics
            is_early_stop = 1 if result_state.termination_cause == "confidence_early_stop" else 0
            
            await self._metrics.record(MetricEvent(
                experiment_id=self._config.experiment_id,
                run_id=self._config.experiment_id,
                question_id=question_id,
                metric_name="early_stop_rate",
                value=is_early_stop,
                unit="count"
            ))
            
            confidence_traj = result_state.metadata.get("confidence_trajectory", [])
            if confidence_traj:
                avg_confidence = sum(c.get("stop_confidence", 0) for c in confidence_traj) / len(confidence_traj)
                await self._metrics.record(MetricEvent(
                    experiment_id=self._config.experiment_id,
                    run_id=self._config.experiment_id,
                    question_id=question_id,
                    metric_name="avg_stop_confidence",
                    value=avg_confidence,
                    unit="pct"
                ))
                
            # Tool Governance Metrics
            suppressed_count = result_state.metadata.get("tools_suppressed_count", 0)
            latency_saved = result_state.metadata.get("tool_latency_saved_ms", 0.0)
            
            await self._metrics.record(MetricEvent(
                experiment_id=self._config.experiment_id,
                run_id=self._config.experiment_id,
                question_id=question_id,
                metric_name="tool_suppression_rate",
                value=suppressed_count,
                unit="count"
            ))
            await self._metrics.record(MetricEvent(
                experiment_id=self._config.experiment_id,
                run_id=self._config.experiment_id,
                question_id=question_id,
                metric_name="avg_latency_saved_ms",
                value=latency_saved,
                unit="ms"
            ))
            
            # Verification Metrics
            verify_history = result_state.verification_history
            trigger_count = len(verify_history)
            failure_count = len([v for v in verify_history if not v.get("is_valid", True)])
            
            await self._metrics.record(MetricEvent(
                experiment_id=self._config.experiment_id,
                run_id=self._config.experiment_id,
                question_id=question_id,
                metric_name="verification_rate",
                value=trigger_count,
                unit="count"
            ))
            await self._metrics.record(MetricEvent(
                experiment_id=self._config.experiment_id,
                run_id=self._config.experiment_id,
                question_id=question_id,
                metric_name="avg_verification_failures",
                value=failure_count,
                unit="count"
            ))
            
            # Compression Metrics
            comp_history = result_state.compression_history
            if comp_history:
                avg_ratio = sum(c.get("decision", {}).get("compression_ratio", 1.0) for c in comp_history) / len(comp_history)
                tokens_saved = sum(c.get("decision", {}).get("original_token_estimate", 0) - c.get("decision", {}).get("compressed_token_estimate", 0) for c in comp_history)
                
                await self._metrics.record(MetricEvent(
                    experiment_id=self._config.experiment_id,
                    run_id=self._config.experiment_id,
                    question_id=question_id,
                    metric_name="avg_compression_ratio",
                    value=avg_ratio,
                    unit="pct"
                ))
                await self._metrics.record(MetricEvent(
                    experiment_id=self._config.experiment_id,
                    run_id=self._config.experiment_id,
                    question_id=question_id,
                    metric_name="total_tokens_saved",
                    value=tokens_saved,
                    unit="tokens"
                ))
            
        return {
            "question_id": question_id,
            "final_answer": result_state.final_answer,
            "total_tokens": result_state.total_tokens,
            "total_latency_ms": result_state.total_latency_ms,
            "steps": len(result_state.steps),
            "is_terminated": result_state.is_terminated,
            "question": question_text,
            "accuracy": scores.get("accuracy", 0.0),
            "exact_match": scores.get("exact_match", 0.0),
            "difficulty_class": diff_pred.get("difficulty_class", "unknown") if diff_pred else "unknown",
            "budget_class": alloc_pred.get("budget_class", "unknown") if alloc_pred else "unknown",
            "runtime_profile": self._config.runtime_profile or "unknown"
        }

    async def _run_calibration(self, results: list[dict[str, Any]]) -> None:
        """Perform telemetry-driven policy adjustment after a batch."""
        engine = CalibrationEngine()
        
        # Aggregate mock metrics from results for calibration
        mock_metrics = []
        for r in results:
            mock_metrics.append({
                "accuracy": r.get("accuracy", 0.0),
                "total_tokens": r.get("total_tokens", 500)
            })
            
        params = global_calibration_manager.get_current_parameters()
        decision = engine.calculate_adjustment(params, mock_metrics)
        
        if decision.parameter_updates:
            new_snapshot = global_calibration_manager.apply_calibration(decision)
            logger.info("self_calibration_applied", 
                        version=new_snapshot.version_id, 
                        rationale=decision.rationale)
            
            # Emit calibration metrics
            for name, val in global_calibration_manager.get_current_parameters().items():
                await self._metrics.record(MetricEvent(
                    experiment_id=self._config.experiment_id,
                    run_id=self._config.experiment_id,
                    question_id="SYSTEM",
                    metric_name=f"calibrated_{name}",
                    value=val,
                    unit="threshold"
                ))
