# PromptOpt — Simplified Roadmap
> Automatic Prompt Optimization Platform
> Version: 2.0 | Updated: 2026-04-28

---

## What We're Building

PromptOpt automatically improves LLM prompts without changing the model. Submit a base prompt, choose how to evaluate it, and the system runs an iterative loop — generating variants, scoring them, and converging on the best version.

**Core loop:**
```
User Input → Job Initializer → Variant Generator
  ├── [with dataset]  → Dataset Scorer → Accuracy Evaluator
  └── [no dataset]    → Criteria Scorer
              └── Score Collector → Converged?
                    ├── No  → back to Variant Generator
                    └── Yes → Ranker → Best Prompt Store → Export API → UI
```

**Two evaluation modes:**
- **Dataset mode** — labeled examples scored by accuracy or LLM-judge
- **Datasetless mode** — plain-English criteria rules, no examples needed

**Stack:** React + Vite (frontend) · FastAPI + SQLite (backend) · Anthropic API

**Design:** Arctic Light — Fraunces + DM Sans + IBM Plex Mono · blue/teal accents

---

## 14 Features Overview

| # | Feature | Layer | Priority |
|---|---|---|---|
| 1 | Job Initializer | Backend | 🔴 Critical |
| 2 | Variant Generator | Backend | 🔴 Critical |
| 3 | Dataset Scorer + Accuracy Evaluator | Backend | 🔴 Critical |
| 4 | Criteria Scorer | Backend | 🔴 Critical |
| 5 | Score Collector + Convergence Check | Backend | 🔴 Critical |
| 6 | Ranker + Best Prompt Store | Backend | 🔴 Critical |
| 7 | Run API Endpoints | Backend | 🔴 Critical |
| 8 | Export API | Backend | 🔴 Critical |
| 9 | Mock Data + api.js | Frontend | 🔴 Critical |
| 10 | App Shell + Routing | Frontend | 🔴 Critical |
| 11 | Dashboard | Frontend | 🔴 Critical |
| 12 | Runs Table + Inspector + Diff Viewer | Frontend | 🔴 Critical |
| 13 | New Run Wizard | Frontend | 🔴 Critical |
| 14 | Prompt Registry | Frontend | 🔴 Critical |

---

## Build Order

```
Frontend first — mock data keeps UI always runnable:

F-01  Mock Data + api.js
F-02  App Shell + Routing
F-03  Dashboard
F-04  Runs Table + Inspector + Diff Viewer
F-05  New Run Wizard
F-06  Prompt Registry

Then backend — wire to real API by setting VITE_DEMO_MODE=false:

B-01  Job Initializer
B-02  Variant Generator
B-03  Dataset Scorer + Accuracy Evaluator
B-04  Criteria Scorer
B-05  Score Collector + Convergence Check
B-06  Ranker + Best Prompt Store
B-07  Run API Endpoints
B-08  Export API
```

---

## Phase 1 — Frontend

**Goal:** All 6 screens fully navigable with realistic mock data. No backend needed.

---

### F-01 — Mock Data + api.js

**Files:** `src/lib/mockData.js`, `src/lib/api.js`

**mockData.js** — realistic mock objects matching real API shapes:
- 6 runs covering all statuses: queued · running ×2 · complete ×2 · failed
- 5 prompt variants per completed run (with diff tokens)
- 4 registry entries: production ×2 · optimizing · draft
- 10 activity events

**Core data shapes:**
```js
// Run
{ id, task_name, task_type, mode, base_prompt, scorer,
  max_iterations, early_stop_threshold, variants_per_iter,
  status, best_score, baseline_score, best_prompt,
  iterations_run, token_count, latency_ms,
  failure_reason, created_at, completed_at }

// Variant
{ id, run_id, iteration, prompt_text, score,
  token_count, latency_ms,
  diff_tokens: [{type: 'add'|'remove'|'equal', text}],
  created_at }

// Registry entry
{ id, task_name, task_type, mode, prompt_text,
  best_score, version, token_count, status, run_id, created_at }
```

**api.js** — all fetch calls in one place. `VITE_DEMO_MODE=true` re-routes to mock functions with 300–700ms artificial delays:
```js
api.getRuns(filters)       // filter: status, mode, task_type
api.getRun(id)
api.getVariants(runId)
api.createRun(config)
api.cancelRun(id)
api.getRegistry(filters)
api.saveToRegistry(runId)
api.exportRun(id, format)  // 'text' | 'json'
api.getVersions(runId)
```

---

### F-02 — App Shell + Routing

**Files:** `App.jsx`, `Sidebar.jsx`, `design-system.css`

**Sidebar nav:**
```
WORKSPACE
  ◈ Dashboard          /
  ↻ Runs          [3]  /runs
  ✦ New Optimization   /wizard

LIBRARY
  ≡ Prompt Registry    /registry
```

**Design system CSS variables:**
```css
--bg:#f4f6f9  --bg2:#ffffff  --bg3:#eef1f6  --bg4:#e4e8f0
--bd:#dde2ed  --bd2:#c8d0e0
--t:#0d1424   --t2:#4a5568   --t3:#8896ac
--ac:#1a6ef5  --ac2:#0f52c4
--gr:#0d9e82  --grb:#e0f5f0
--am:#d97706  --amb:#fef3e0
--re:#dc2626  --reb:#fde8e8
--bl:#2563eb  --blb:#e8f0fe
--pu:#7c3aed  --pub:#f0ebfe
--mono:'IBM Plex Mono',monospace
--sans:'DM Sans',sans-serif
--disp:'Fraunces',serif
--shadow: 0 1px 3px rgba(13,20,36,.08)
```

**Routes:** `/` Dashboard · `/runs` RunsPage · `/wizard` OptimizationWizard · `/registry` PromptRegistry

**Reusable Topbar component:** accepts `title` prop + action button children

**Sidebar behaviour:**
- Active item: `background: rgba(26,110,245,.09)`, 2px blue left border, `color: var(--ac2)`
- Hover: `background: var(--bg3)`
- Run badge: blue pill showing count of running runs

---

### F-03 — Dashboard

**File:** `components/Dashboard.jsx`

**Layout:**
```
[StatCard ×4]
[Score Chart]     [Activity Feed]
[Active Run Cards]
```

**Stat cards (4 — computed from mock run data):**
- Best Score → `max(best_score)` across completed runs · green top border
- Active Runs → count where `status === 'running'` · blue top border
- Avg Improvement → avg of `(best_score - baseline_score)` · amber top border
- Total Variants → sum of `iterations_run × variants_per_iter` · purple top border

**Score chart:** Recharts `LineChart`. Data: completed runs ordered by `created_at`. X = run labels (r1…rN). Y = `best_score`. Green line `var(--gr)`. Horizontal grid lines only.

**Activity feed:** 5 most recent events. Dot color by type:
- `run_complete` / `prompt_saved` → green
- `run_started` / `iter_complete` → blue
- `early_stop` → amber
- `run_failed` → red

**Active run cards:** One per running run. Shows: ID · task name · scorer+mode subtitle · progress bar · current best score.

---

### F-04 — Runs Table + Inspector + Diff Viewer

**Files:** `components/RunsPage.jsx`, `components/RunInspector.jsx`, `src/lib/diff.js`

**Runs page layout:**
```
[Topbar]
[Tabs: All · Completed · Running · Failed]
[Table — flex:1]              [Inspector — 370px, right-docked]
```

**Table columns:** Run ID · Task name · Type tag · Mode · Score bar · Tokens · Iters · Status pill · Time ago

**Filter bar:** Search (by task_name, debounced 300ms) + chips: All / With dataset / No dataset

**Tabs:** filter by `status`

**Row click:** highlights row, loads run into inspector

**Inspector panel:**
- Header: run ID + "↗ Full view" button
- 4 metric boxes: Best score · Baseline · Tokens · Latency
- SVG sparkline: one dot per iteration, last dot green and larger
- Prompt diff viewer (component below)
- Run log: scrollable, mono 11px, `[INFO]` blue · `[SCORE]`/`[DONE]` green · `[ERROR]` red
- Buttons: `↓ Export` (navigates to registry with run pre-selected) · `⊞ Save to registry`

**diff.js — word-level LCS algorithm:**
```js
export function computeDiff(baseText, optimizedText)
// Tokenise by words → compute LCS matrix → backtrack
// Returns: Array<{type: 'add'|'remove'|'equal', text: string}>
```

**DiffViewer component:** renders diff tokens as inline spans:
- `equal` → `color: var(--t2)`
- `add` → `background: #d1fae5`, `color: #065f46`, border-radius 3px
- `remove` → `background: #fee2e2`, `color: #991b1b`, strikethrough

Truncate at 800 chars, "Show more" button expands.

**Status pills:** running (blue + pulse dot) · complete (green) · failed (red) · queued (grey)

**Task type tags:** classification (blue) · summarization (purple) · extraction (amber) · judge (green)

---

### F-05 — New Run Wizard

**File:** `components/OptimizationWizard.jsx`

**4 steps with left sidebar step tracker (240px):**
```
Step 1: Task Config
Step 2: Base Prompt
Step 3: Dataset / Criteria
Step 4: Run Config + Launch
```

**Step tracker states:**
- Done: green circle + ✓ + summary text in subtitle
- Current: blue circle + step number
- Todo: grey circle + step number

**Step 1 — Task Config:**
- Task name: text input, required
- Task type: dropdown (Classification · Summarization · Extraction · Judge · Generation)

**Step 2 — Base Prompt:**
- Textarea, mono font, min-height 160px
- Token counter: `Math.round(text.length / 4)` / 4000 tokens
- Next disabled if empty or >4000 tokens

**Step 3 — Dataset / Criteria:**

Mode toggle — two full-width selectable cards:
```
[📊 With dataset]              [✏️ No dataset]
Labeled examples               Define criteria rules
for objective scoring          no examples needed
```

**With dataset selected** → JSON textarea:
```
Paste labeled examples as JSON:
[{"input": "...", "label": "..."}, ...]
```
Validate on every change: must be array, each item needs `input` + `label`.
Show: "N examples loaded · JSON valid ✓" (green) or specific error (red).

**No dataset selected** → Criteria builder:
- List of rule items (text + × remove button)
- "Add a rule…" input + "+ Add" button, Enter key support
- Pre-suggest 2 starter rules based on task type
- Minimum 1 rule to proceed

**Step 4 — Run Config:**
```
Max iterations          slider 2–20,    default 8,    live value display
Early stop threshold    slider 0.5–1.0, default 0.92, live value display
Variants per iteration  slider 2–10,    default 5,    live value display
```
Scorer auto-set: dataset mode → Accuracy · nodataset → LLM Judge (shown as read-only info)

**Launch button:** `✦ Launch optimization run →` full width, blue primary. On click:
1. Validate all steps
2. Call `api.createRun(config)`
3. Navigate to `/runs` with new run ID highlighted

---

### F-06 — Prompt Registry

**File:** `components/PromptRegistry.jsx`

**Layout:**
```
[Topbar: "Prompt Registry"]   [✦ New prompt]
[Tabs: All · Production · Optimizing · Draft]
[Search + filter chips]
[2-column card grid]
```

**Card structure:**
```
┌─ HEADER ──────────────────────────────┐
│ Task name (13.5px, 500)   Status pill │
│ Mode label (grey, 11.5px)             │
├─ BODY ────────────────────────────────┤
│ Prompt preview (mono, 3-line clamp)   │
│ Score  Version  Tokens      Type tag  │
├─ FOOTER (bg3) ────────────────────────┤
│ [↓ Export]  [⊞ History]  [↻ Re-opt]  │
└───────────────────────────────────────┘
```

**Export (↓):** Downloads prompt as `.txt` file using Blob API.

**History (⊞):** Opens slide-in drawer from right. Shows version list ordered newest → oldest. Each row: version badge · label · score · time. Click a row → loads that version's prompt text into a preview box above the list.

**Re-optimize (↻):** Navigates to `/wizard` with `base_prompt` pre-filled from this entry.

**Status pills:** production (green) · optimizing (blue + pulse dot) · draft (grey)

**Filter chips:** All types · With dataset · No dataset

---

## Phase 2 — Backend

**Goal:** Full FastAPI backend. Switch `VITE_DEMO_MODE=false` to wire frontend to real data.

---

### B-01 — Job Initializer

**File:** `backend/core/job_initializer.py`

**RunConfig Pydantic model with validators:**
- `mode=dataset` → dataset required, ≥1 item, each needs `input` + `label`
- `mode=nodataset` → criteria required, ≥1 rule
- `scorer=accuracy` only valid when `mode=dataset`
- `base_prompt` max 16000 chars

**SQLite schema (two tables):**
```sql
runs: id, task_name, task_type, mode, base_prompt, scorer,
      max_iterations, early_stop_threshold, variants_per_iter,
      dataset_json, criteria_json, status, best_score, baseline_score,
      best_prompt, iterations_run, token_count, latency_ms,
      failure_reason, created_at, completed_at

prompt_variants: id, run_id, iteration, prompt_text, score,
                 token_count, latency_ms, diff_json, created_at
```

**`create_run(config)` returns:** `{ id: "run-{uuid8}", status: "queued", created_at }`

---

### B-02 — Variant Generator

**File:** `backend/core/variant_generator.py`

**`generate_variants(prompt, task_type, task_name, n_variants, feedback)` → `list[str]`**

Uses `claude-sonnet-4-5`. Meta-prompt instructs LLM to rewrite the prompt N times, returning a JSON array of strings. One template per task type (classification, summarization, extraction, judge, generation).

**Requirements:** retry ×3 with exponential backoff · parse JSON array · deduplicate · return exactly N variants

---

### B-03 — Dataset Scorer + Accuracy Evaluator

**File:** `backend/core/scorer.py`

```python
async def run_on_dataset(variant, dataset) -> list[dict]
# Calls LLM once per example, up to 5 in parallel
# Returns: [{input, label, model_output, correct}]

def accuracy_score(scored_outputs) -> float
# case-insensitive: exact match → substring → first-word
# Returns float 0–1

async def llm_judge_score(variant, task_type, outputs) -> float
# LLM rates each output 0–1, returns average
# Used when mode=nodataset and scorer=llm_judge
```

---

### B-04 — Criteria Scorer

**File:** `backend/core/criteria_scorer.py`

```python
async def criteria_score(variant, criteria, test_input) -> dict
# Runs variant on test_input, then asks LLM to judge each rule
# Returns: { score: float, rule_results: [{rule, passed, reason}] }
# score = rules_passed / total_rules
```

Judge prompt per rule: "Does this output satisfy the rule: '{rule}'? Answer YES or NO with one reason sentence."

---

### B-05 — Score Collector + Convergence Check

**File:** `backend/core/optimizer.py`

```python
def normalise_score(raw, scorer_type) -> float
# Clips to [0.0, 1.0]. All current scorers already return 0–1.

def check_convergence(best_score, threshold, iterations_run, max_iterations, score_history)
# Returns (converged: bool, reason: str)
# Stops on: score >= threshold · iterations >= max · no improvement in last 2 iters

async def run_optimization(run_id: str)
# Main loop:
# 1. Load config · set status=running · score base prompt (baseline)
# 2. Loop: generate → score → normalise → pick best → check convergence
# 3. Rank · store best · set status=complete
```

---

### B-06 — Ranker + Best Prompt Store

**File:** `backend/core/ranker.py`

```python
def rank_variants(variants) -> list[dict]
# Sort: score DESC → token_count ASC → latency_ms ASC

def store_best(run_id, best_variant) -> None
# Update runs: best_prompt, best_score, token_count, latency_ms, status, completed_at
# Insert all variants into prompt_variants table
```

---

### B-07 — Run API Endpoints

**File:** `backend/routers/runs.py`, `backend/main.py`

| Method | Path | Description |
|---|---|---|
| POST | `/runs` | Create run + start optimizer as background task |
| GET | `/runs` | List runs, filter by status / mode / task_type |
| GET | `/runs/{id}` | Get single run |
| DELETE | `/runs/{id}` | Cancel queued or running run |
| GET | `/runs/{id}/variants` | All variants ordered by iteration |

**main.py:** FastAPI app · CORS for `localhost:5173` · SQLite init on startup · include all routers

**requirements.txt:** fastapi · uvicorn · pydantic≥2 · anthropic · python-multipart

---

### B-08 — Export API

**File:** `backend/routers/export.py`

| Method | Path | Description |
|---|---|---|
| GET | `/runs/{id}/export?format=text` | Best prompt as plain string |
| GET | `/runs/{id}/export?format=json` | Best prompt + full metadata |
| GET | `/runs/{id}/versions` | All iterations ordered by score |
| POST | `/registry` | Save run's best prompt to registry |
| GET | `/registry` | List registry entries (filter by status) |
| PATCH | `/registry/{id}` | Update status (production/draft/archived) |

---

## Project File Structure

```
promptopt/
├── roadmap.md
├── progress.md
├── prompt.md
│
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── .env                     ← VITE_DEMO_MODE=true
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── design-system.css
│       ├── lib/
│       │   ├── mockData.js
│       │   ├── api.js
│       │   └── diff.js
│       ├── hooks/
│       │   └── useOptimizationRun.js
│       └── components/
│           ├── Sidebar.jsx
│           ├── Dashboard.jsx
│           ├── RunsPage.jsx
│           ├── RunInspector.jsx
│           ├── DiffViewer.jsx
│           ├── OptimizationWizard.jsx
│           └── PromptRegistry.jsx
│
└── backend/
    ├── main.py
    ├── requirements.txt
    ├── routers/
    │   ├── runs.py
    │   └── export.py
    └── core/
        ├── job_initializer.py
        ├── variant_generator.py
        ├── scorer.py
        ├── criteria_scorer.py
        ├── optimizer.py
        └── ranker.py
```

---

## Definition of Done

Each feature is done when:
- [ ] Works with mock data (frontend) or passes unit tests (backend)
- [ ] No console/runtime errors
- [ ] Handles empty and error states
- [ ] Matches Arctic Light design system
- [ ] `progress.md` updated with status

---

*roadmap.md v2.0 — PromptOpt simplified · 2026-04-28*
