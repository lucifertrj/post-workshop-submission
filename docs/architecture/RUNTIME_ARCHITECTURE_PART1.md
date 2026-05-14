# ATTCO — Runtime Execution Architecture Specification
## Part 1 of 3: Topology · Graph Execution · State Management
### Classification: Principal Architecture Review | v0.1.0

---

## PREAMBLE: WHAT ATTCO IS AT RUNTIME

At runtime, ATTCO is not a repository, an API, or a script collection.

ATTCO is a **runtime adaptive inference optimization platform** — a stateful, event-driven,
async orchestration engine that:

- ingests research queries from benchmark datasets
- executes cyclic reasoning graphs over LLM inference calls
- continuously applies optimizer modules at every graph transition
- captures every execution event into a structured telemetry stream
- aggregates performance metrics into a queryable analytical store
- produces immutable, versioned, replayable experiment artifacts

The runtime architecture is the real system. Everything else is scaffolding.

---

## 1. GLOBAL RUNTIME TOPOLOGY

### 1.1 Execution Layers

ATTCO's runtime is organized into six strictly bounded execution layers.
Each layer has exactly one responsibility. Cross-layer coupling is prohibited.

```
LAYER 6 — VISUALIZATION & ANALYTICS LAYER
          Streamlit · Plotly · DuckDB queries · Parquet reads

LAYER 5 — ARTIFACT & PERSISTENCE LAYER
          DuckDB · Parquet · Redis · Local FS · Trace archives

LAYER 4 — OBSERVABILITY LAYER
          Structured Tracer · LangSmith · structlog · Metrics Collector

LAYER 3 — OPTIMIZATION LAYER
          Optimizer Registry · Optimizer Pipeline · Arbitration Engine

LAYER 2 — ORCHESTRATION LAYER
          LangGraph StateGraph · Node Executor · Routing Engine

LAYER 1 — INGESTION LAYER
          Benchmark Runner · Dataset Loader · Experiment Registry
```

Layer contracts:
- Layer N may only communicate downward to Layer N-1 or N-2
- Layer N may never directly read from Layer N+1
- Observability (Layer 4) receives push events from all layers
- Persistence (Layer 5) is written by Layer 4 only; read by Layer 6 only

### 1.2 Runtime Orchestration Hierarchy

```
ExperimentController  (singleton per benchmark run)
  |
  |-- ExperimentRegistry       (registers + versions the run)
  |-- DatasetIngestionPipeline (loads + shards benchmark)
  |
  +-- BenchmarkScheduler
        |
        +-- AsyncWorkerPool    (N concurrent evaluation workers)
              |
              +-- [Worker 1..N]
                    |
                    +-- GraphExecutionContext
                          |
                          |-- LangGraph StateGraph
                          |     |-- ReasonNode
                          |     |-- ActNode
                          |     |-- ObserveNode
                          |     |-- VerifyNode (conditional)
                          |     +-- TerminateNode
                          |
                          |-- OptimizerPipeline
                          |     +-- [Optimizer 1..M]
                          |
                          +-- ExecutionTracer

  |-- MetricsCollector    (receives events from all workers)
  +-- TraceAggregator     (aggregates spans from all workers)
```

### 1.3 Query Execution Flow — End to End

```
[1]  QUERY INGESTION
     BenchmarkScheduler dequeues question Q from evaluation queue.
     ExperimentController assigns: experiment_id, run_id, question_id.
     ExecutionContext initialized with frozen config snapshot.

[2]  GRAPH INITIALIZATION
     LangGraph StateGraph compiled from registered topology.
     AgentState initialized: question, IDs, empty step history.
     TraceEvent(GRAPH_STARTED) emitted.

[3]  REASON NODE
     LiteLLM async completion call with current prompt context.
     Thought token stream received and parsed.
     TraceEvent(REASONING_STEP_STARTED) emitted.
     Token delta tracked via token_tracker processor.

[4]  OPTIMIZER EVALUATION (after every node transition)
     OptimizerPipeline receives serialized AgentState snapshot.
     All active optimizers evaluate in precedence order.
     Arbitration Engine resolves conflicts.
     OptimizerDecision (continue / terminate / reroute) returned.
     TraceEvent(OPTIMIZER_DECISION) emitted.

[5]  CONDITIONAL ROUTING
     Router reads OptimizerDecision + current state.
     Routes to: ActNode | VerifyNode | TerminateNode.
     Graph edge conditional resolved.

[6]  ACT NODE
     Tool call parsed from thought output.
     Tool invoked asynchronously via ToolRegistry.
     TraceEvent(TOOL_INVOCATION) emitted (start + end).
     Latency tracked via latency_tracker processor.

[7]  OBSERVE NODE
     Tool output processed and appended to AgentState.
     TraceEvent(REASONING_STEP_COMPLETED) emitted.

[8]  CYCLE DECISION
     If is_terminated = True --> TerminateNode --> END.
     Else --> back to REASON NODE.

[9]  TERMINATION
     TerminateNode closes state: final_answer, ended_at, total_tokens.
     TraceEvent(EXECUTION_TERMINATED) emitted.
     MetricEvent batch emitted for all per-run metrics.

[10] ARTIFACT PERSISTENCE
     Trace events flushed to TraceStore (JSONL / Parquet).
     Metric events flushed to MetricsStore (DuckDB).
     Config snapshot archived to artifacts/ directory.
     RunSummary written to DuckDB run_summaries table.

[11] BENCHMARK AGGREGATION
     After all workers complete, BenchmarkScheduler aggregates.
     Accuracy, latency distributions, token statistics computed.
     BenchmarkResult artifact written.
     TraceEvent(BENCHMARK_COMPLETED) emitted.

[12] VISUALIZATION AVAILABILITY
     Dashboard reads DuckDB / Parquet from artifacts/.
     Plotly charts rendered from aggregated metrics.
     Trace explorer reads JSONL trace archives.
```

---

## 2. LANGGRAPH EXECUTION ARCHITECTURE

### 2.1 Why LangGraph is Architecturally Correct for ATTCO

| Requirement | Why LangGraph |
|---|---|
| Cyclic reasoning | Supports cycles natively; LCEL/chains do not |
| Conditional routing | Edge conditionals are first-class graph primitives |
| Stateful execution | State is threaded through all nodes as a single schema |
| Interruptibility | Supports graph interrupts for optimizer gating |
| Checkpointing | Checkpointers persist state between steps |
| Async execution | All nodes execute as async coroutines |
| Composability | Subgraphs can be embedded for modular pipelines |
| Observability | LangSmith integration is native |

### 2.2 Graph Topology

```
GRAPH ENTRY (AgentState init)
      |
      v
  REASON NODE  <-----------------------------------------+
  (LLM thought)                                          |
      |                                                  |
      v                                                  |
  OPTIMIZER GATE (post-reason)                           |
      |               |                                  |
   continue        terminate                             |
      |               |                                  |
      v               v                                  |
  ACT NODE     TERMINATE NODE --> END                    |
  (tool invoke)                                          |
      |                                                  |
      v                                                  |
  OBSERVE NODE                                           |
      |                                                  |
      v                                                  |
  OPTIMIZER GATE (post-observe)                          |
      |          |           |                           |
   continue   verify      terminate                      |
      |          |           |                           |
      +----------+           v                           |
      |       VERIFY NODE  TERMINATE NODE --> END        |
      |       (conditional)                              |
      |           |                                      |
      +-----------+--------------------------------------+
```

### 2.3 Node Contracts

Every node is bound by this execution contract:

```
Node Contract
  Input:        Immutable AgentState snapshot
  Output:       Updated AgentState (new object)
  Side effects: ONLY via Tracer.emit() — no direct I/O otherwise
  Async:        All nodes are async coroutines
  Error:        Nodes catch exceptions, update state.error, emit error event
  Timeout:      Every node has a configured execution timeout
  Idempotency:  Node re-execution on same state must be safe
```

Node responsibility matrix:

| Node | Reads | Writes | External I/O |
|---|---|---|---|
| ReasonNode | steps, question | steps (new step) | LiteLLM (async) |
| ActNode | steps[-1].action | steps[-1].tool_calls | ToolRegistry (async) |
| ObserveNode | steps[-1].tool_calls | steps[-1].observation | None |
| VerifyNode | steps, final_answer | metadata.verified | LiteLLM (async) |
| TerminateNode | steps | is_terminated, ended_at | None |

### 2.4 Conditional Routing Semantics

**Deterministic edges** (always taken):
- ReasonNode → ActNode
- ActNode → ObserveNode
- TerminateNode → END

**Conditional edges** (routing function decides):
- ObserveNode → {ReasonNode | VerifyNode | TerminateNode}
- VerifyNode → {ReasonNode | TerminateNode}

The routing function is **pure** — same inputs always produce same output.
This is critical for determinism and replayability.

### 2.5 Termination Guarantees

The ATTCO graph is provably terminating under these guarantees:

1. Step counter monotonically increases on every ReasonNode execution
2. DepthControllerOptimizer terminates at configurable max_steps
3. TokenBudgetOptimizer terminates at configurable token limit
4. ObserveNode detects final answer pattern and sets is_terminated=True
5. GraphExecutionContext enforces wall-clock timeout per question

No infinite loops are possible when at least one condition is active.

### 2.6 Checkpointing Strategy

Checkpoint triggers:
- After every node completion
- Before every optimizer evaluation
- On graph interrupt

Checkpoint content:
- Full serialized AgentState (Pydantic v2 JSON)
- Step index and graph node position
- Timestamp

Checkpoint storage:
- Local: SQLite via LangGraph's SqliteSaver
- Future: Redis via RedisSaver for distributed execution

Replay semantics:
A failed execution can be resumed from the last checkpoint by reinitializing
the graph with the persisted thread_id. This is the foundation of ATTCO's
execution replayability model.

---

## 3. STATE MANAGEMENT ARCHITECTURE

### 3.1 State Classification

| State Domain | Owner | Mutable | Lifecycle | Persistence |
|---|---|---|---|---|
| AgentState | GraphExecutionContext | Yes (within run) | Query lifetime | Checkpointed |
| ExperimentState | ExperimentController | Immutable after init | Experiment lifetime | Artifact archive |
| OptimizerState | OptimizerPipeline | Stateless per eval | Per eval | Not persisted |
| BenchmarkState | BenchmarkScheduler | Append-only | Benchmark run | DuckDB |
| TelemetryState | Tracer | Append-only | Platform lifetime | JSONL / Parquet |
| MetricsState | MetricsStore | Append-only | Platform lifetime | DuckDB / Parquet |

### 3.2 AgentState Lifecycle

```
INIT
  AgentState created with: experiment_id, run_id, question_id, question
  Immutable fields set: run_id, experiment_id, question_id, question, started_at
  All other fields initialized to defaults

ACTIVE (graph executing)
  Mutable fields updated on each node transition:
  - steps: append-only list of ReasoningStep objects
  - total_tokens: monotonically increasing integer
  - total_latency_ms: monotonically increasing float
  - metadata: open dict for optimizer annotations

TERMINATED
  is_terminated = True (irreversible boolean flip)
  ended_at = datetime.utcnow() (immutable after set)
  final_answer = string (immutable after set)

ARCHIVED
  Serialized to JSON and written to artifacts/{run_id}/state.json
  Frozen, immutable, queryable
```

### 3.3 Event Sourcing Philosophy

The canonical record of execution is **not the final AgentState** —
it is the **ordered sequence of TraceEvents** emitted during execution.

The final AgentState can be reconstructed by replaying the TraceEvent stream.
This gives ATTCO:
- Full execution replayability
- Step-level debugging
- State reconstruction at any point in history
- Diff-ability between experiment runs

**Event sourcing contract:**
Every AgentState mutation MUST have a corresponding TraceEvent.
No silent state changes are permitted.

### 3.4 Mutable vs Immutable State

**Immutable** (set at init, never changed):
- run_id, experiment_id, question_id, question, started_at
- Config snapshot (frozen), ExperimentRecord (all fields)

**Append-only** (can grow, never shrink or modify):
- AgentState.steps — new ReasoningStep appended, never edited
- TraceEvent log — events appended, never modified
- MetricEvent log — events appended, never modified

**Mutable, bounded**:
- AgentState.total_tokens — monotonically increases
- AgentState.total_latency_ms — monotonically increases
- AgentState.metadata — open annotation dict

**Termination fields** (set exactly once):
- AgentState.is_terminated — False → True, never reversed
- AgentState.ended_at — None → datetime, never changed
- AgentState.final_answer — None → string, never changed

### 3.5 Optimizer State Interaction Model

Optimizers are **stateless** between evaluations. They receive a serialized
snapshot of AgentState (a plain dict). They return an OptimizerDecision
(a value object, not a state mutation directive).

The OptimizerPipeline translates OptimizerDecisions into routing decisions
by annotating AgentState.metadata before returning to the graph router.

This design ensures:
- Optimizer modules can be hot-swapped without state corruption
- Optimizer decisions are fully observable (emitted as TraceEvents)
- Optimizer composition is arbitrated at a single point
- Replay with different optimizers is safe and deterministic

### 3.6 Serialization Strategy

All state objects use **Pydantic v2 model_dump_json()** for serialization:
- JSON is the canonical wire format for checkpointing and archiving
- Parquet is the canonical format for analytical storage
- All datetime fields are UTC-normalized before serialization
- UUID fields serialize as lowercase hyphenated strings
- Nested objects (ReasoningStep, ToolCall) are always fully expanded

---

*ATTCO Runtime Architecture — Part 1 of 3*
*See RUNTIME_ARCHITECTURE_PART2.md and RUNTIME_ARCHITECTURE_PART3.md*
