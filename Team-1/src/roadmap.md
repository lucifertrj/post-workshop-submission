# roadmap.md — ACE Text-to-SQL Project

## Project: Self-Improving Text-to-SQL Agent via ACE
**Model**: qwen2.5-coder (Ollama) | **Dataset**: BIRD Benchmark
**Estimated duration**: 4–5 weeks

---

## Phase 0 — Environment & Baseline

**Goal**: Get everything running and record the "before ACE" numbers. Nothing else matters until this is solid.

### Tasks

- Install Ollama, pull `qwen2.5-coder`, verify the model runs:
  ```bash
  ollama pull qwen2.5-coder
  python -c "from ollama import chat; print(chat(model='qwen2.5-coder', messages=[{'role':'user','content':'SELECT 1'}]).message.content)"
  ```
- Download BIRD dev set and databases — verify SQLite files open cleanly
- Pick **3 databases** from BIRD spanning different domains (e.g. `california_schools`, `financial`, `hockey`) — these are your test domains for the whole project
- Build the `executor.py` module — takes SQL + db_id, runs against SQLite, returns `{success, result, error, rows_returned}`
- Build the basic Generator (no playbook yet) — schema injection only:
  ```
  system: "You are a SQLite expert. Schema: {schema}"
  user: "Question: {question}\nEvidence: {evidence}\nReturn SQL only."
  ```
- Run BIRD's official `evaluation.py` on your baseline — record EX accuracy per difficulty level per database
- This is your **control condition** — store these numbers, they go into your report Table 1

### Deliverable
Working text-to-SQL pipeline with recorded baseline EX numbers. The "before" state.

---

## Phase 1 — Three-Role ACE Architecture

**Goal**: Build all three agents — Generator, Reflector, Curator — as separate modules with the correct prompts. Wire them together in a CLI loop.

### Generator (`src/generator.py`)

Uses the full Generator prompt from `context.md`. Key additions over the baseline:
- Reads playbook from `playbooks/{db_id}_playbook.txt` (empty at first)
- Injects playbook into system prompt under `## PLAYBOOK`
- Returns JSON: `{reasoning, bullet_ids, final_answer}`
- Parse `final_answer` to extract the SQL string

```python
def generate(question, db_id, evidence, schema) -> dict:
    playbook = read_playbook(db_id)
    system = GENERATOR_SYSTEM_PROMPT.format(playbook=playbook, schema=schema)
    user = GENERATOR_USER_TEMPLATE.format(evidence=evidence, question=question)
    raw = call_llm(system, user, expect_json=True)
    return json.loads(raw)  # {reasoning, bullet_ids, final_answer}
```

### Reflector (`src/reflector.py`)

Runs after *every* interaction — successes and failures:
- On failure: identifies error type, extracts insight, flags for curator
- On success: increments helpful counters for cited bullets (via curator UPDATE)
- Returns JSON: `{reasoning, error_identification, root_cause_analysis, correct_approach, key_insight, bullet_tags, outcome}`

```python
def reflect(question, evidence, generated_sql, execution_output,
            expected_output, user_feedback, bullet_ids) -> dict:
    system = REFLECTOR_SYSTEM_PROMPT
    user = REFLECTOR_USER_TEMPLATE.format(...)
    raw = call_llm(system, user, expect_json=True)
    return json.loads(raw)
```

### Curator (`src/curator.py`)

Only runs if Reflector produced a `key_insight` (non-empty string):
- Reads current playbook
- Produces ADD/UPDATE/REMOVE operations
- Calls `playbook.apply_operations(db_id, operations)` to persist

```python
def curate(db_id, reflector_output) -> list:
    playbook = read_playbook(db_id)
    system = CURATOR_SYSTEM_PROMPT
    user = CURATOR_USER_TEMPLATE.format(playbook=playbook,
                                         reflector_output=json.dumps(reflector_output))
    raw = call_llm(system, user, expect_json=True)
    if raw.strip() == "NO_OPERATIONS":
        return []
    result = json.loads(raw)
    return result.get("operations", [])
```

### Playbook (`src/playbook.py`)

```python
def read_playbook(db_id) -> str:
    path = f"playbooks/{db_id}_playbook.txt"
    if not os.path.exists(path):
        return "## STRATEGIES & INSIGHTS\n\n(no entries yet)"
    return open(path).read()

def apply_operations(db_id, operations):
    # Parse current playbook, apply ADD/UPDATE/REMOVE, write back
    # ADD: append new [slug-NNNNN] entry with correct counter format
    # UPDATE: find bullet_id, increment helpful/harmful counters
    # REMOVE: delete bullet line if conditions met
    ...

def get_entry_count(db_id) -> int:
    playbook = read_playbook(db_id)
    return len(re.findall(r'\[(?:str|err|calc|code|prob|ctx|misc)-\d+\]', playbook))
```

### CLI Loop (`main.py`)

Wire the full loop for manual testing:
```
User types question
  → Generator produces SQL + bullet_ids
  → Executor runs SQL
  → Show result to user
  → Collect feedback (explicit + implicit)
  → Reflector analyses
  → Curator updates playbook if needed
  → Log to interactions.jsonl
  → Repeat
```

Test with 30–40 manual queries across all 3 databases. Verify the playbook grows correctly and entries make sense.

### Deliverable
Full ACE loop working in CLI. Playbook file grows after failures. Generator starts citing entries.

---

## Phase 2 — Feedback Collection

**Goal**: Make the feedback loop robust for both manual testing and automated batch runs.

### Explicit feedback (`src/feedback.py`)

```python
def collect_explicit_feedback(question, sql, result) -> dict:
    print(f"\nResult: {result['result']}")
    correct = input("Was this correct? (y/n): ").strip().lower()
    expected = ""
    sql_feedback = ""
    if correct == 'n':
        expected = input("What did you expect? ").strip()
        sql_feedback = input("Any issue with the SQL? (enter to skip): ").strip()
    return {
        "correct": correct == 'y',
        "expected_output": expected,
        "sql_feedback": sql_feedback
    }
```

### Implicit feedback

Before asking the user, check automatically:
- `result['error'] is not None` → SQL error, set `failure_type = "sql_error"`, skip user prompt, pass error message as `expected_output` to Reflector
- `result['rows_returned'] == 0` and question starts with what/which/find/list → likely wrong, ask user to confirm
- Result is a single number but question asks for a list → flag as `failure_type = "wrong_shape"`

### Batch mode (for `run_experiment.py`)

In batch mode, feedback comes from BIRD ground truth automatically:
- Run gold SQL → get gold result
- Run generated SQL → get generated result
- Compare → `correct = (generated_result == gold_result)`
- Pass comparison result as `expected_output` to Reflector
- No human in the loop

### Deliverable
Feedback module works in both interactive (human) and batch (automated) modes.

---

## Phase 3 — Controlled Experiment & Measurement

**Goal**: Produce the numbers that prove ACE works. This is what gets graded.

### Experiment Design (`run_experiment.py`)

Run the same 150 BIRD questions (50 per database, balanced across difficulties) under two conditions:

**Condition A — Static Baseline:**
- `playbook_enabled = False`
- Generator uses schema + evidence only, no playbook
- Record EX accuracy

**Condition B — ACE Agent:**
- `playbook_enabled = True`
- Playbook starts empty, grows from implicit feedback (BIRD gold truth as ground truth)
- After each query: Reflector runs, Curator updates if needed
- Record EX accuracy at iteration 1, 5, 10, 20, 50, 100

### Metrics to collect and plot

```python
# Every N iterations, record:
{
  "iteration": 20,
  "ex_all": 0.62,
  "ex_simple": 0.78,
  "ex_moderate": 0.55,
  "ex_challenging": 0.41,
  "playbook_entry_count": 14,
  "playbook_token_size": 2840,
  "helpful_bullet_ratio": 0.86  # bullets with helpful > harmful
}
```

Save to `results/experiment_TIMESTAMP.csv`. Plot:
1. EX accuracy over iterations: ACE vs Static (main result graph)
2. EX by difficulty: simple/moderate/challenging separately
3. Playbook size over iterations (proves grow-and-refine, no collapse)
4. Error type breakdown at iteration 1 vs 50 (wrong_column, wrong_filter, wrong_join, sql_error)

### Finding the convergence point

Run until EX stops improving across 10 consecutive iterations. This is the convergence point — report it honestly. It is a feature, not a failure: it shows the playbook has captured all learnable heuristics for this schema.

### Statistical check

Run Condition B three times with different random question orderings. Report mean and standard deviation of final EX. This shows results are stable and not order-dependent.

### Deliverable
CSV + graphs showing improvement curve. These go directly into the report.

---

## Phase 4 — Streamlit Demo Application

**Goal**: Make the project visible and presentable in a live demo.

### Layout (`app.py`)

Two-column layout:

**Left column — Chat interface:**
- Database selector dropdown (db_id)
- Text input for question
- Generated SQL displayed in code block
- Execution result as a dataframe table
- Success/failure indicator
- Feedback form (correct? expected? SQL issue?)

**Right column — Live playbook viewer:**
- Shows current `{db_id}_playbook.txt` rendered as markdown
- Entry count at the top: `14 entries | 2,840 tokens`
- Auto-refreshes after every interaction
- Color-coded: entries with `helpful > 3` highlighted green, `harmful > 0` highlighted amber

**Sidebar:**
- "Reset playbook" button — clears current db_id's playbook to empty
- "Baseline mode" toggle — disables playbook for side-by-side comparison
- Entry count history chart (sparkline of growth over session)

### Demo script (record this as a video for submission)

1. Start with empty playbook, baseline mode ON — show a query failing
2. Switch to ACE mode — same query, still fails (playbook empty)
3. Give feedback — watch playbook update in the right panel in real time
4. Ask 5 more similar queries — show EX improving
5. Ask the original failing query again — now correct
6. Press "Reset playbook" — show it fails again
7. Switch database — show playbook starts fresh, re-learns from zero

### Deliverable
Streamlit app that runs locally. 3–5 minute demo video.

---

## Phase 5 — Report

**Structure:**

1. **Abstract** — one paragraph: problem, method, result (lead with the number)
2. **Introduction** — why text-to-SQL is hard, why static prompts fail on BIRD, what ACE adds
3. **Background** — ACE paper (Generator/Reflector/Curator roles, brevity bias, context collapse) + BIRD paper (scale, external knowledge challenge, EX metric)
4. **Methodology** — your pipeline: three-role architecture, playbook format with helpful/harmful counters, feedback design, grow-and-refine principle
5. **Experiments** — dataset details (which 3 databases, how many questions, difficulty split), evaluation setup, baseline description
6. **Results** — graphs from Phase 3, honest analysis including where ACE didn't help (simple questions)
7. **Convergence Analysis** — at what iteration does the playbook saturate? This is your original contribution beyond the paper
8. **Limitations** — cross-database generalisation, very large schemas, qwen2.5-coder size constraints
9. **Conclusion**

**Honest claims to make:**
- ACE improves EX accuracy on BIRD without any model retraining
- Improvement is strongest on moderate and challenging questions
- Simple questions show less improvement (schema heuristics matter less when the query is trivial)
- Playbook converges at approximately N iterations per database — characterising this is novel
- The three-role separation (Generator/Reflector/Curator) prevents context collapse that monolithic rewriting would cause

---

## What Success Looks Like

| Criterion | Target |
|---|---|
| EX improvement over static baseline | +5–15% by iteration 50 |
| Strongest gains on | moderate / challenging difficulty |
| Playbook entries at convergence | 15–40 per database |
| Context collapse | Zero — playbook only grows |
| Demo runs live | Full loop visible in Streamlit, < 5 min |
| Report convergence analysis | Novel finding not in original paper |
