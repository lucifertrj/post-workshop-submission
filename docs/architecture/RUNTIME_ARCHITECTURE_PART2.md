# ATTCO — Runtime Execution Architecture Specification
## Part 2 of 3: Event Model · Telemetry · Benchmarking · Optimizer Runtime
### Classification: Principal Architecture Review | v0.1.0

---

## 4. EVENT-DRIVEN EXECUTION MODEL

### 4.1 Architectural Philosophy

ATTCO treats every significant execution event as a first-class, named,
structured, immutable data object. The event stream is the primary
observability surface for the entire platform. No significant execution
transition occurs without a corresponding event being emitted.

**Event-driven principles applied:**

1. **Decoupling** — Producers emit events without knowing who consumes them
2. **Observability** — Any system behavior can be reconstructed from the event log
3. **Replayability** — The event stream can be replayed to reproduce execution
4. **Traceability** — Every event carries correlation IDs for span reconstruction
5. **Composability** — New consumers (dashboards, alerting) attach without producer changes

### 4.2 Event Taxonomy

```
Event Superclass: SystemEvent
  |
  +-- InferenceEvent       (LLM calls, token streams, completions)
  +-- GraphEvent           (graph start, node transitions, termination)
  +-- OptimizerEvent       (optimizer evaluations, decisions, overrides)
  +-- ToolEvent            (tool invocations, results, errors)
  +-- BenchmarkEvent       (benchmark start/complete, question batch events)
  +-- TelemetryEvent       (trace emission, metric flush, artifact write)
  +-- ExperimentEvent      (registration, versioning, config freeze)
```

### 4.3 Canonical Event Definitions

| Event Name | Class | Producer | Consumers |
|---|---|---|---|
| QUERY_RECEIVED | BenchmarkEvent | BenchmarkScheduler | Tracer, MetricsCollector |
| GRAPH_STARTED | GraphEvent | GraphExecutionContext | Tracer |
| REASONING_STEP_STARTED | GraphEvent | ReasonNode | Tracer, MetricsCollector |
| LLM_CALL_STARTED | InferenceEvent | ReasonNode / VerifyNode | Tracer |
| LLM_CALL_COMPLETED | InferenceEvent | ReasonNode / VerifyNode | Tracer, MetricsCollector |
| OPTIMIZER_EVALUATED | OptimizerEvent | OptimizerPipeline | Tracer |
| OPTIMIZER_DECISION | OptimizerEvent | Arbitration Engine | Tracer, Router |
| TOOL_INVOCATION_STARTED | ToolEvent | ActNode | Tracer |
| TOOL_INVOCATION_COMPLETED | ToolEvent | ActNode | Tracer, MetricsCollector |
| TOOL_INVOCATION_FAILED | ToolEvent | ActNode | Tracer, MetricsCollector |
| REASONING_STEP_COMPLETED | GraphEvent | ObserveNode | Tracer, MetricsCollector |
| VERIFICATION_TRIGGERED | OptimizerEvent | OptimizerPipeline | Tracer |
| VERIFICATION_COMPLETED | OptimizerEvent | VerifyNode | Tracer, MetricsCollector |
| EXECUTION_TERMINATED | GraphEvent | TerminateNode | Tracer, MetricsCollector |
| METRIC_RECORDED | TelemetryEvent | MetricsCollector | MetricsStore |
| TRACE_FLUSHED | TelemetryEvent | Tracer | TraceStore |
| BENCHMARK_STARTED | BenchmarkEvent | BenchmarkScheduler | Tracer |
| BENCHMARK_COMPLETED | BenchmarkEvent | BenchmarkScheduler | Tracer, MetricsStore |
| EXPERIMENT_REGISTERED | ExperimentEvent | ExperimentRegistry | Tracer |

### 4.4 Event Schema Contract

All events implement this canonical schema:

```
SystemEvent (canonical schema)
  event_id:        UUID         -- globally unique per event
  experiment_id:   string       -- ties event to experiment
  run_id:          string       -- ties event to specific run
  question_id:     string       -- ties event to specific question
  event_class:     EventClass   -- taxonomy enum
  event_type:      string       -- specific event name (see table above)
  step:            int          -- ReAct step index at emission time
  timestamp_utc:   datetime     -- UTC timestamp, microsecond precision
  payload:         dict         -- event-specific structured data
  token_delta:     int | None   -- tokens consumed since last step
  latency_ms:      float | None -- latency contribution of this event
  model_id:        str | None   -- LLM model ID if inference event
  node_id:         str | None   -- graph node that emitted this event
  span_id:         UUID         -- groups events within one node execution
  parent_span_id:  UUID | None  -- enables nested span hierarchies
```

### 4.5 Correlation ID Propagation

ATTCO uses a four-level correlation hierarchy:

```
experiment_id  (top level — unique per experiment config)
    |
    run_id     (unique per benchmark run — one run has many questions)
        |
        question_id  (unique per benchmark question)
            |
            span_id  (unique per node execution within a question)
```

Every event carries all four IDs. This enables:
- All events for an experiment: filter by experiment_id
- All events for a run: filter by run_id
- Full execution trace for one question: filter by question_id
- All events within one reasoning step: filter by span_id

### 4.6 Event Ordering Guarantees

Within a single worker (single asyncio task):
- Events are emitted in strict causal order
- Ordering is guaranteed by the sequential nature of async await chains

Across workers (concurrent benchmark execution):
- Events are ordered by timestamp_utc within each question's trace
- Cross-question ordering is not guaranteed and not required
- Each question's event stream is self-contained and independently replayable

### 4.7 Event Transport Architecture

```
Producer (any ATTCO node/module)
    |
    | tracer.emit(event)     [async, non-blocking — queue push]
    v
Internal AsyncQueue          [bounded, backpressure-aware]
    |
    | background drain task  [single async drain coroutine per tracer]
    v
Backend Router               [fans out to all registered backends]
    |
    +-- LangSmith backend    [async HTTP push to LangSmith API]
    +-- structlog backend    [async structured log write]
    +-- Local JSONL backend  [async file append]
```

The critical design principle: **event emission NEVER blocks the hot path**.
The `tracer.emit()` call is always a non-blocking queue push.
The drain loop operates independently in the background.

---

## 5. TELEMETRY & OBSERVABILITY ARCHITECTURE

### 5.1 Observability Hierarchy

ATTCO implements a three-tier observability model:

```
TIER 1 — EXECUTION TRACES (highest fidelity)
  Every event at every step. Full execution reconstruction.
  Storage: JSONL per run_id, archived to Parquet per experiment.
  Query: By question_id, span_id, event_class, event_type.
  Retention: Indefinite (research artifact).

TIER 2 — STRUCTURED LOGS (medium fidelity)
  Per-node INFO/DEBUG logs via structlog.
  Always carries: trace_id, run_id, question_id, node_id.
  Storage: Log files, or external aggregator (Loki, CloudWatch).
  Retention: Configurable (default 30 days).

TIER 3 — METRICS (aggregated)
  Aggregated statistics per run, per experiment.
  Storage: DuckDB + Parquet.
  Query: SQL via DuckDB for dashboard rendering.
  Retention: Indefinite (analytical artifact).
```

### 5.2 Span Architecture

ATTCO defines five span types that map directly to observability concepts:

**GraphSpan** — one per question execution
```
  start: GRAPH_STARTED event
  end:   EXECUTION_TERMINATED event
  contains: all child spans below
  key fields: total_tokens, total_latency_ms, step_count
```

**ReasoningSpan** — one per ReAct step
```
  start: REASONING_STEP_STARTED
  end:   REASONING_STEP_COMPLETED
  parent: GraphSpan
  key fields: tokens_this_step, thought_text, action_parsed
```

**InferenceSpan** — one per LLM call
```
  start: LLM_CALL_STARTED
  end:   LLM_CALL_COMPLETED
  parent: ReasoningSpan or VerificationSpan
  key fields: model_id, prompt_tokens, completion_tokens, latency_ms
```

**ToolSpan** — one per tool invocation
```
  start: TOOL_INVOCATION_STARTED
  end:   TOOL_INVOCATION_COMPLETED or TOOL_INVOCATION_FAILED
  parent: ReasoningSpan
  key fields: tool_name, tool_input, tool_output, latency_ms
```

**OptimizerSpan** — one per optimizer pipeline evaluation
```
  start: OPTIMIZER_EVALUATED
  end:   OPTIMIZER_DECISION
  parent: ReasoningSpan
  key fields: optimizer_name, decision, reason, evaluated_at_step
```

### 5.3 LangSmith Integration Model

LangSmith is the primary deep-inspection observability backend.

ATTCO's LangSmith integration model:
- Every GraphSpan maps to one LangSmith Run
- Every ReasoningSpan maps to one LangSmith Child Run
- Every InferenceSpan maps to one LangSmith LLM Call
- Metadata includes: experiment_id, optimizer_config, step budgets
- Tags include: benchmark_name, optimizer_active, model_id

The LangSmith backend is activated via environment configuration.
It is never the only active backend — structlog always runs in parallel.

### 5.4 Metrics Aggregation Topology

```
Runtime Events (all layers)
    |
    | MetricsCollector.record(MetricEvent)
    v
AsyncQueue (bounded, 50k capacity)
    |
    | periodic flush (every N seconds)
    v
DuckDB MetricsStore
    |
    +-- metric_events table    (raw events, queryable by any dimension)
    +-- run_summaries table    (pre-aggregated per run)
    |
    +-- Parquet export         (on benchmark completion, for archival)

DuckDB MetricsStore (read path)
    |
    | SQL queries from Dashboard
    v
Plotly visualization components
```

### 5.5 Correlation ID Propagation in Logs

Every structlog log statement in ATTCO carries bound context vars:
- `trace_id` — HTTP request trace ID (API layer)
- `experiment_id` — current experiment
- `run_id` — current benchmark run
- `question_id` — current question being evaluated
- `node_id` — current LangGraph node

These are bound once per execution context and automatically included
in every log line from that context. This enables full log correlation
across all subsystems without manual parameter passing.

---

## 6. BENCHMARK EXECUTION TOPOLOGY

### 6.1 Benchmark Lifecycle

```
PHASE 1 — REGISTRATION
  ExperimentRegistry.register(name, config) called.
  experiment_id assigned. Config snapshot frozen.
  Git SHA recorded. ExperimentRecord persisted.

PHASE 2 — DATASET INGESTION
  DatasetIngestionPipeline loads benchmark via HuggingFace datasets.
  Dataset version hash recorded (for reproducibility).
  Questions filtered/shuffled with fixed random seed.
  Questions sharded into worker batches.

PHASE 3 — SCHEDULING
  BenchmarkScheduler initializes AsyncWorkerPool.
  Evaluation queue populated with all question batches.
  MetricsCollector started (background flush loop).
  Tracer started (background drain loop).
  TraceEvent(BENCHMARK_STARTED) emitted.

PHASE 4 — CONCURRENT EXECUTION
  Worker pool executes questions concurrently up to concurrency limit.
  Each worker runs a GraphExecutionContext independently.
  No shared mutable state between workers (each has own AgentState).
  Redis used for cross-worker progress tracking (optional).

PHASE 5 — AGGREGATION
  BenchmarkScheduler collects all BenchmarkResult objects.
  RunSummary computed: accuracy, latency distributions, token stats.
  TraceEvent(BENCHMARK_COMPLETED) emitted.
  RunSummary written to DuckDB.

PHASE 6 — ARTIFACT ARCHIVAL
  Metric events flushed from queue to DuckDB.
  Trace events flushed from queue to JSONL files.
  Parquet exports written for both metrics and traces.
  Config snapshot and git SHA written to artifacts bundle.
```

### 6.2 Concurrency Model for Benchmark Execution

```
BenchmarkScheduler
    |
    +-- asyncio.Semaphore(concurrency_limit)
    |
    +-- asyncio.gather(*[evaluate(q) for q in questions], return_exceptions=True)
              |
              +-- Worker 1: GraphExecutionContext (own event loop tasks)
              +-- Worker 2: GraphExecutionContext
              +-- Worker N: GraphExecutionContext
```

Concurrency limit is configurable per benchmark config.
Each worker runs within the **same** event loop (single-process async model).
Workers share the event loop but do not share mutable state.
The Semaphore ensures at most N workers run simultaneously.

### 6.3 Benchmark Suite Execution Model

For each supported benchmark:

**HotpotQA** — multi-hop reasoning
```
  Dataset: HuggingFace hotpot_qa (fullwiki split)
  Question type: 2-hop factual reasoning requiring tool use
  Evaluation metric: Exact Match + F1 on final answer
  Expected agent behavior: 2-4 ReAct steps per question
  Recommended concurrency: 4-8 workers
```

**GSM8K** — mathematical reasoning
```
  Dataset: HuggingFace gsm8k (main split)
  Question type: Multi-step arithmetic word problems
  Evaluation metric: Exact numerical match
  Expected agent behavior: 3-6 ReAct steps, calculator tool use
  Recommended concurrency: 8-16 workers (no external API per step)
```

**TriviaQA** — factual retrieval
```
  Dataset: HuggingFace trivia_qa (rc.wikipedia split)
  Question type: Single-hop factual retrieval
  Evaluation metric: Exact Match + F1
  Expected agent behavior: 1-3 ReAct steps
  Recommended concurrency: 8-16 workers
```

**MMLU** — knowledge breadth
```
  Dataset: HuggingFace cais/mmlu (all subjects)
  Question type: Multiple choice across 57 subjects
  Evaluation metric: Accuracy (choice A/B/C/D)
  Expected agent behavior: 1-2 ReAct steps (knowledge retrieval)
  Recommended concurrency: 16+ workers
```

### 6.4 Failure Recovery Strategy

**Question-level failure:**
- Wrapped in `return_exceptions=True` in asyncio.gather
- Failed questions logged with full exception trace
- Run continues without the failed question
- Failed question IDs recorded in RunSummary.failed_ids
- Partial run results are still valid and archived

**Worker crash recovery:**
- LangGraph checkpoint allows resume from last graph step
- Resume triggered by resubmitting question with same thread_id
- Partial trace events already emitted are preserved

**Backend failure (LangSmith / Redis unavailable):**
- Non-critical backends fail silently; error logged
- Local JSONL backend always active as fallback
- DuckDB write failures cause hard failure (metrics integrity critical)

**Partial run recovery:**
- Completed question results preserved in DuckDB before failure
- Re-run command with `resume_from=run_id` resumes from first unanswered question
- Config snapshot compared to ensure no config drift between runs

---

## 7. OPTIMIZER RUNTIME ARCHITECTURE

### 7.1 Optimizer Lifecycle

```
REGISTRATION (at startup)
  All optimizer classes registered via @register decorator.
  OptimizerRegistry populated before any benchmark execution.

INSTANTIATION (per experiment)
  OptimizerPipeline built from experiment config.
  Each optimizer instantiated with its config object.
  Pipeline ordered by configured precedence list.

EVALUATION (per graph node transition)
  OptimizerPipeline.evaluate(state_snapshot) called.
  Each optimizer evaluates independently and returns OptimizerDecision.
  Arbitration Engine resolves conflicting decisions.
  Single OptimizerDecision returned to graph Router.

DECISION APPLICATION
  Router reads OptimizerDecision.
  If terminate: route to TerminateNode.
  If reroute: route to non-default next node.
  If continue: route to default next node.
  Annotation written to AgentState.metadata.

TEARDOWN (after experiment)
  No cleanup needed — optimizers are stateless.
```

### 7.2 Optimizer Composition Model

Multiple optimizers can be active simultaneously. Their interaction is:

```
OptimizerPipeline receives: AgentState snapshot
    |
    +-- DepthControllerOptimizer.evaluate(snapshot)  -> Decision A
    +-- TokenBudgetOptimizer.evaluate(snapshot)       -> Decision B
    +-- VerifierGatingOptimizer.evaluate(snapshot)    -> Decision C
    +-- ToolPrunerOptimizer.evaluate(snapshot)        -> Decision D
    |
    v
ArbitrationEngine.resolve([A, B, C, D])
    |
    v
Single OptimizerDecision returned
```

### 7.3 Arbitration Logic

The ArbitrationEngine applies these precedence rules:

**Termination is always highest precedence:**
- If ANY optimizer returns `should_continue=False`, execution terminates
- No other optimizer can override a termination decision

**Verification is higher precedence than rerouting:**
- If VerifierGating returns `route_to=verify`, this overrides default routing
- But does NOT override termination

**Continue decisions require unanimous agreement:**
- All active optimizers must return `should_continue=True` for execution to continue
- This is the strictest safety guarantee

**Exception: disabled optimizers are ignored in arbitration:**
- An optimizer with `enabled=False` returns a neutral decision
- Neutral decisions are excluded from arbitration

### 7.4 Optimizer Contract Enforcement

The base class contract that all optimizers must satisfy:

```
Contract verification at registration:
  - evaluate() must be async
  - evaluate() must accept dict[str, Any] as state_snapshot
  - evaluate() must return OptimizerDecision
  - evaluate() must NOT modify the state_snapshot dict
  - evaluate() must NOT perform I/O (no LLM calls, no DB reads)
  - evaluate() must complete within configured timeout
  - evaluate() must be idempotent given the same input
```

**Violations of these contracts are detected by the contract test suite
in tests/unit/test_optimizer_base.py.**

### 7.5 Optimizer Runtime Interaction with Six Key Capabilities

**Adaptive Depth Control:**
- Optimizer reads: `state_snapshot["step_count"]`
- Termination condition: `step_count >= config.max_depth`
- Decision: terminate
- Annotation: `metadata["termination_reason"] = "max_depth_reached"`

**Token Budgeting:**
- Optimizer reads: `state_snapshot["total_tokens"]`
- Termination condition: `total_tokens >= config.budget_tokens`
- Soft warning at: `total_tokens >= budget * soft_limit_fraction`
- Decision: terminate (hard) or reroute to verify (soft)

**Verification Gating:**
- Optimizer reads: `state_snapshot["step_count"]`, metadata flags
- Trigger condition: configurable (every N steps, or on low-confidence signal)
- Decision: reroute to VerifyNode
- Purpose: selectively trigger self-verification without running it every step

**Tool Pruning:**
- Optimizer reads: `state_snapshot["steps"][-1]["tool_calls"]`
- Trigger condition: tool error rate exceeds threshold, or tool not useful this question type
- Decision: annotate `metadata["disabled_tools"]` — ActNode reads this before tool selection

**Confidence Routing:**
- Optimizer reads: `state_snapshot["metadata"]["confidence_estimate"]`
- Termination condition: `confidence >= config.exit_threshold`
- Decision: terminate (early exit on high confidence)

**Trace Compression:**
- Optimizer reads: `state_snapshot["steps"]` length
- Trigger condition: context approaching max_tokens of LLM
- Decision: annotate `metadata["compress_context"] = True`
- ReasonNode reads annotation and applies context compression before next LLM call

---

*ATTCO Runtime Architecture — Part 2 of 3*
*See RUNTIME_ARCHITECTURE_PART3.md*
