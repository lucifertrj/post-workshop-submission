# ATTCO — Runtime Execution Architecture Specification
## Part 3 of 3: Metrics · Reproducibility · Artifacts · Async Model · Distribution
### Classification: Principal Architecture Review | v0.1.0

---

## 8. METRICS LIFECYCLE ARCHITECTURE

### 8.1 Metrics as First-Class Runtime Citizens

Metrics in ATTCO are not afterthoughts added to track performance.
They are **first-class runtime outputs** — as important as the final answers.

The research questions ATTCO investigates are answered by metrics:
- Does adaptive depth control reduce tokens without sacrificing accuracy?
- What is the efficiency-accuracy tradeoff curve for token budgeting?
- At what reasoning depth does tool usage become counterproductive?
- How does latency scale with step count under different optimizer configs?

These questions are only answerable if the metrics infrastructure is
as rigorous as the reasoning infrastructure.

### 8.2 Metric Generation Points

Every significant runtime event is a potential metric generation point.
Metrics are generated at six levels:

**Step-level metrics** (per ReAct step):
- `tokens_per_step` — tokens consumed in this step
- `latency_per_step_ms` — wall clock for this step
- `tool_calls_per_step` — number of tool invocations
- `thought_length_chars` — characters in thought text

**Question-level metrics** (per benchmark question):
- `latency_total_ms` — total wall clock from query to answer
- `tokens_input_total` — total prompt tokens consumed
- `tokens_output_total` — total completion tokens generated
- `step_count_total` — total ReAct steps executed
- `tool_call_count_total` — total tool invocations
- `tool_error_count` — tool failures
- `task_accuracy` — binary: correct / incorrect
- `optimizer_termination_reason` — what caused termination
- `verification_triggered` — boolean: was verify node invoked

**Run-level metrics** (per benchmark run, aggregated):
- `accuracy_mean`, `accuracy_by_question_type`
- `latency_mean`, `latency_p50`, `latency_p95`, `latency_p99`
- `tokens_input_mean`, `tokens_output_mean`, `tokens_total_mean`
- `step_count_mean`, `step_count_distribution`
- `tool_call_count_mean`, `tool_error_rate`
- `efficiency_ratio` — accuracy / tokens_total_mean

**Experiment-level metrics** (across multiple runs):
- `baseline_vs_optimized_accuracy_delta`
- `baseline_vs_optimized_latency_delta_pct`
- `baseline_vs_optimized_token_delta_pct`
- `efficiency_improvement_ratio`

**Optimizer-specific metrics**:
- `depth_controller_terminations_pct` — % questions terminated by depth
- `token_budget_terminations_pct`
- `verification_trigger_rate`
- `early_exit_rate`

**Trace-derived metrics** (computed post-run from trace archives):
- `reasoning_chain_entropy` — diversity of thought patterns
- `tool_selection_consistency` — does agent pick same tools for similar questions
- `step_redundancy_rate` — steps that contributed no new information

### 8.3 Metrics Pipeline

```
Runtime Event occurs
    |
    | MetricsCollector.record(MetricEvent)   [async, fire-and-forget]
    v
AsyncQueue (50k capacity, backpressure-aware)
    |
    | Background flush loop (every 5 seconds or on benchmark completion)
    v
MetricsStore.write_event(event)             [DuckDB INSERT]
    |
    v
DuckDB (metric_events table)
    |
    +-- Incremental aggregation during run
    |       (run_summaries updated after each question completion)
    |
    +-- Parquet export on benchmark completion
    |       (immutable analytical archive)
    |
    +-- Polars DataFrame API for ad-hoc analysis
    |
    +-- SQL query surface for Dashboard (Streamlit + Plotly)
```

### 8.4 Metric Comparison Architecture

The benchmark comparator (benchmarks/comparator.py) enables the core
research capability of ATTCO: comparing baseline vs optimized systems.

**Comparison model:**
```
ComparatorInput:
  baseline_run_id:    string   (run with optimizer=none)
  optimized_run_id:   string   (run with specific optimizer config)
  metrics_to_compare: list     (configurable subset of metrics)

ComparatorOutput:
  delta_report:       dict     (absolute and relative deltas per metric)
  significance:       dict     (statistical significance where applicable)
  tradeoff_matrix:   dict     (accuracy vs tokens vs latency tradeoffs)
  recommendation:    string    (architect-level efficiency assessment)
```

### 8.5 Visualization Flow

```
DuckDB MetricsStore
    |
    | SQL: SELECT ... FROM run_summaries WHERE experiment_id = ?
    v
Polars DataFrame
    |
    v
Plotly chart components (visualization/plots/)
    |
    +-- latency_curves.py     -- per-step latency distributions
    +-- token_heatmaps.py     -- token consumption by question type
    +-- accuracy_tradeoffs.py -- efficiency-accuracy Pareto curves
    +-- trace_timelines.py    -- step-by-step execution gantt charts
    |
    v
Streamlit Dashboard (dashboard/pages/)
    |
    +-- overview.py          -- experiment summary
    +-- trace_explorer.py    -- question-level trace drill-down
    +-- metrics_comparison.py -- baseline vs optimized comparisons
    +-- token_analytics.py   -- token consumption analytics
```

---

## 9. EXPERIMENT REPRODUCIBILITY ARCHITECTURE

### 9.1 Reproducibility as a First-Class Requirement

Research value depends entirely on reproducibility. A benchmark result
that cannot be reproduced is worthless. ATTCO's architecture treats
reproducibility as a mandatory system property, not a best-effort practice.

**Reproducibility definition for ATTCO:**
Given the same `experiment_id`, a researcher must be able to:
1. Reconstruct the exact config used
2. Reconstruct the exact dataset used
3. Re-execute the same agent behavior (within LLM stochasticity bounds)
4. Produce the same aggregate metrics (within sampling variance)
5. Produce the same trace structure (same steps, same routing decisions)

### 9.2 Reproducibility Guarantee Stack

```
LAYER 1 — CONFIG REPRODUCIBILITY
  Every experiment freezes its full Hydra config at registration time.
  Config snapshot stored as: artifacts/{experiment_id}/config_snapshot.yaml
  Config is never modified after registration.
  Reproduction: load config_snapshot.yaml and run with --config-path override.

LAYER 2 — CODE REPRODUCIBILITY
  Git SHA recorded at experiment registration.
  Git SHA stored as: artifacts/{experiment_id}/git_sha.txt
  Reproduction requires: git checkout {git_sha} before re-run.
  CI enforces: no uncommitted changes when running benchmark experiments.

LAYER 3 — DATASET REPRODUCIBILITY
  HuggingFace dataset version hash recorded at ingestion time.
  Dataset hash stored in ExperimentRecord.
  Same dataset split + version hash = identical question set.
  Questions shuffled with fixed random_seed from experiment config.
  Reproduction: same dataset hash + same random_seed = identical question order.

LAYER 4 — EXECUTION REPRODUCIBILITY
  Random seeds set at three levels:
    - Python random.seed(config.random_seed)
    - numpy random seed (for any ML components)
    - LiteLLM call: temperature=0.0 for deterministic LLM outputs
  Reproduction: same seeds + temperature=0.0 = identical reasoning chains.

LAYER 5 — DEPENDENCY REPRODUCIBILITY
  uv.lock commits exact dependency versions.
  Docker images tagged with git SHA.
  Reproduction: docker pull attco:{git_sha} = identical runtime environment.
```

### 9.3 Experiment Registration Protocol

When `ExperimentRegistry.register()` is called:

1. Unique `experiment_id` (UUID) assigned
2. `ExperimentRecord` created with:
   - experiment_id
   - name
   - config_snapshot (full Hydra config dict, deeply frozen)
   - git_sha (from subprocess git rev-parse)
   - created_at (UTC timestamp)
   - dataset_hash (populated after ingestion)
   - random_seed (from config)
3. Record persisted to DuckDB experiments table
4. TraceEvent(EXPERIMENT_REGISTERED) emitted
5. Artifact directory created: `artifacts/{experiment_id}/`
6. Config snapshot written to artifact directory

**No execution begins until registration is confirmed.**
This ensures every run has a complete audit trail before first event.

### 9.4 Execution Signature

Every benchmark result is signed with an **ExecutionSignature**:

```
ExecutionSignature:
  experiment_id:    UUID
  git_sha:          string
  config_hash:      sha256 of config_snapshot JSON
  dataset_hash:     HuggingFace dataset version hash
  random_seed:      int
  dependency_hash:  sha256 of uv.lock
  created_at:       UTC timestamp

Signature stored in: artifacts/{experiment_id}/signature.json
```

Two runs with identical ExecutionSignatures are considered **reproducible**.
Divergent results from identical signatures indicate LLM stochasticity or
external API non-determinism — both of which are documented in the RunSummary.

---

## 10. ARTIFACT MANAGEMENT ARCHITECTURE

### 10.1 Artifact Hierarchy

```
artifacts/
    |
    +-- {experiment_id}/
    |       |
    |       +-- config_snapshot.yaml    [Hydra config at registration]
    |       +-- git_sha.txt             [Code version]
    |       +-- signature.json          [ExecutionSignature]
    |       +-- experiment_record.json  [ExperimentRecord]
    |       |
    |       +-- runs/
    |               |
    |               +-- {run_id}/
    |                       |
    |                       +-- traces/
    |                       |       +-- {question_id}.jsonl    [per-question trace]
    |                       |
    |                       +-- metrics/
    |                       |       +-- metric_events.parquet  [raw metrics]
    |                       |       +-- run_summary.json       [aggregated summary]
    |                       |
    |                       +-- results/
    |                       |       +-- benchmark_results.json [final results]
    |                       |       +-- comparison_report.json [vs baseline]
    |                       |
    |                       +-- state/
    |                               +-- {question_id}.json     [final AgentState]
```

### 10.2 Artifact Immutability Contract

Once written, artifacts are **never modified**:
- Trace JSONL files are append-during-run, sealed after run completion
- Parquet files are written once at run completion, never updated
- config_snapshot.yaml is written at registration, never changed
- RunSummary JSON is written at run completion, never updated

If a re-run is needed, a **new experiment_id** is assigned.
The old artifacts are preserved indefinitely.

### 10.3 Artifact Storage Model

**Local (default):**
- All artifacts written to `artifacts/` directory in repo root
- DuckDB files co-located at `artifacts/metrics.duckdb`
- Total storage estimate: ~50MB per 1000 questions (traces + metrics)

**Future S3/GCS (distributed):**
- Artifact paths become S3/GCS URIs
- DuckDB replaced by external DuckDB with S3 Parquet scanning
- Local cache maintained for hot artifacts (Redis-backed)

### 10.4 Artifact Querying Model

**Trace querying:**
```
# By question (exact trace for one question)
traces/{run_id}/{question_id}.jsonl  →  read directly

# By event_class across a run
SELECT * FROM read_parquet('artifacts/*/traces/*.parquet')
WHERE event_class = 'OPTIMIZER_DECISION'
AND run_id = ?
```

**Metrics querying:**
```
# Run-level summary
SELECT * FROM run_summaries WHERE experiment_id = ?

# Cross-run comparison
SELECT r1.accuracy, r2.accuracy, r1.tokens_total_mean, r2.tokens_total_mean
FROM run_summaries r1, run_summaries r2
WHERE r1.experiment_id = ? AND r2.experiment_id = ?
```

---

## 11. ASYNC & CONCURRENCY MODEL

### 11.1 Single-Process Async Architecture

ATTCO's current architecture is **single-process, multi-coroutine**.

```
Single Python Process
    |
    +-- Main asyncio Event Loop (uvloop)
          |
          +-- BenchmarkScheduler coroutine
          |       |
          |       +-- asyncio.gather over N worker coroutines
          |               |
          |               +-- Worker 1: GraphExecutionContext
          |               |       |
          |               |       +-- LangGraph node coroutines
          |               |       +-- LiteLLM acompletion awaits
          |               |       +-- ToolRegistry async calls
          |               |
          |               +-- Worker N: GraphExecutionContext
          |
          +-- MetricsCollector drain loop (background task)
          +-- Tracer drain loop (background task)
          +-- LangSmith push loop (background task)
```

### 11.2 Backpressure Model

ATTCO uses **queue-based backpressure** at every async boundary:

| Queue | Producer | Consumer | Capacity | On Full |
|---|---|---|---|---|
| Tracer internal queue | All modules | Tracer drain loop | 10,000 events | Log warning, drop event |
| MetricsCollector queue | All modules | Metrics flush loop | 50,000 events | Log warning, drop event |
| Benchmark evaluation queue | BenchmarkScheduler | Worker pool | All questions | Bounded by question count |
| LangSmith push queue | Tracer | LangSmith backend | 5,000 events | Retry with backoff |

Queue drops are always logged with event metadata (never silently discarded).
Drop events themselves generate a `TELEMETRY_DROP` SystemEvent.

### 11.3 Worker Lifecycle

```
Worker lifecycle (per GraphExecutionContext):

CREATED:    Worker instantiated with question, experiment_id, run_id
STARTED:    AgentState initialized, TraceEvent(GRAPH_STARTED) emitted
EXECUTING:  Cycling through graph nodes, awaiting LLM calls and tool calls
COMPLETED:  Final answer produced, TraceEvent(EXECUTION_TERMINATED) emitted
ARCHIVED:   State and traces flushed to persistence layer
TORN DOWN:  Worker references released, no cleanup needed (stateless workers)
```

### 11.4 Cancellation and Timeout Semantics

**Per-question timeout:**
- Each worker wrapped in `asyncio.wait_for(coroutine, timeout=config.timeout_s)`
- Timeout raises `asyncio.TimeoutError`
- Worker catches TimeoutError, emits `EXECUTION_TERMINATED(reason=timeout)`
- Question recorded as failed with timeout reason
- Metrics still collected for partial execution

**Graceful shutdown:**
- SIGTERM triggers graceful shutdown sequence
- BenchmarkScheduler stops accepting new questions
- Remaining in-flight workers allowed to complete (with deadline)
- All queues drained before process exits
- Final Parquet exports written
- DuckDB connection closed cleanly

**Hard shutdown (SIGKILL):**
- In-flight results for incomplete questions are lost
- DuckDB WAL ensures no metric corruption
- Trace JSONL files may be truncated (incomplete traces)
- Partial runs resumable from checkpoint if thread_id preserved

### 11.5 Scheduling Policy

Current scheduling: **FIFO with Semaphore bound** (simple, deterministic)

Questions processed in fixed order (sorted by question_id after shuffle with seed).
This ensures deterministic processing order across runs with the same seed.

Future scheduling options:
- **Priority scheduling** — harder questions (by estimated steps) processed first
- **Adaptive scheduling** — dynamically adjust concurrency based on LLM latency
- **Batched scheduling** — group similar questions for context-efficient processing

---

## 12. FUTURE DISTRIBUTED EXECUTION PREPARATION

### 12.1 Architectural Choices That Enable Distribution

Every key architectural decision in ATTCO was made with distributed scaling in mind:

| Decision | Local Benefit | Distributed Benefit |
|---|---|---|
| Shared-nothing worker model | Simple reasoning | Workers trivially distribute to separate processes/machines |
| Event-based observability | Full traceability | Events can be routed to distributed message brokers |
| Append-only metrics | Simple writes | Partitioned by run_id across multiple DuckDB instances |
| Config-driven execution | Reproducibility | Config can be serialized and sent to remote workers |
| Correlation IDs everywhere | Local debugging | Distributed trace correlation via OpenTelemetry |
| Checkpointed state | Local resilience | Checkpoints stored in Redis enable cross-machine resume |

### 12.2 Distribution Migration Path

**Phase 1 — Local async (current)**
```
Single process, uvloop event loop, asyncio Semaphore concurrency.
Sufficient for: up to ~200 concurrent questions, single machine.
```

**Phase 2 — Multi-worker (Redis orchestration)**
```
Multiple Python processes, each running a worker pool.
Redis pub/sub for work distribution (question_id pushed to Redis queue).
Redis for shared benchmark state (progress tracking).
DuckDB replaced by centralized PostgreSQL or shared Parquet on NFS.
Sufficient for: up to 1,000 concurrent questions, 4-8 machines.
```

**Phase 3 — Distributed (Ray or Celery)**
```
Ray remote actors or Celery workers for GraphExecutionContext.
Object store (S3/GCS) for artifact persistence.
OpenTelemetry for distributed trace correlation.
Apache Kafka for event stream (replaces in-process async queues).
Prometheus + Grafana for operational metrics.
Sufficient for: unlimited concurrency, cloud-native deployment.
```

### 12.3 Distributed Tracing Preparation

ATTCO's correlation ID model (experiment_id / run_id / question_id / span_id)
is **isomorphic to OpenTelemetry's Trace/Span model**:

| ATTCO | OpenTelemetry |
|---|---|
| experiment_id | Trace ID (top-level) |
| run_id | Second-level span |
| question_id | Third-level span |
| span_id | Leaf span |
| event_type | Span name |
| timestamp_utc | Span start/end |
| latency_ms | Span duration |

Migration to OpenTelemetry requires only a new TracerBackend implementation
that wraps OTEL SDK calls. No changes to producers (ATTCO modules) are needed.

### 12.4 Distributed State Management Preparation

LangGraph's checkpointer abstraction enables distributed state:
- Local SQLite (current) → swap to RedisSaver with zero code changes in graph
- RedisSaver allows worker handoff: Worker A checkpoints, Worker B resumes
- This is the critical primitive for distributed execution

### 12.5 Distributed Metrics Aggregation

Current DuckDB MetricsStore → future distributed aggregation:

```
Local Phase:
  Each worker writes to shared DuckDB on local filesystem.

Distributed Phase:
  Each worker writes Parquet shards to S3.
  DuckDB (with httpfs extension) scans S3 Parquet directly.
  No dedicated metrics server needed for analytics queries.
  For operational monitoring: Prometheus + push gateway per worker.
```

---

## APPENDIX: RUNTIME ENGINEERING GOVERNANCE

### Invariants That Must Never Be Violated

1. **Event emission never blocks execution** — all `tracer.emit()` calls are fire-and-forget
2. **Optimizers never mutate AgentState directly** — all state changes via return values
3. **Workers share no mutable state** — each GraphExecutionContext is independent
4. **Config snapshots are immutable after registration** — no runtime config changes
5. **Trace events are append-only** — no event modification after emission
6. **Metric events are append-only** — no retroactive metric correction
7. **Termination is irreversible** — is_terminated=True can never be reset
8. **All LLM calls are async** — no blocking inference calls in any coroutine
9. **Artifact directories are monotonically growing** — no file deletion after write
10. **Experiment IDs are globally unique** — UUID v4, never reused

### Runtime Health Indicators

| Indicator | Healthy | Concerning |
|---|---|---|
| Tracer queue depth | < 1,000 events | > 5,000 events |
| Metrics queue depth | < 5,000 events | > 25,000 events |
| Worker completion rate | > 95% | < 90% |
| Tool error rate | < 5% | > 15% |
| LLM timeout rate | < 2% | > 5% |
| Checkpoint write latency | < 100ms | > 500ms |

---

*ATTCO Runtime Architecture — Part 3 of 3 (Complete)*
*Document: RUNTIME_ARCHITECTURE_PART1.md + PART2.md + PART3.md*
*Classification: Principal Architecture Review | v0.1.0*
