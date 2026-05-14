# PromptOpt — Progress Tracker
> Automatic Prompt Optimization Platform
> Session: 03 | Updated: 2026-04-28

---

## ✅ Completed

### Planning & Research
- Analyzed real-world APO tools: ProTeGi (Microsoft), APE, Evidently AI, AutoPDL
- Mapped core optimization loop from v2 flowchart (confirmed final — no changes needed)
- Identified UI reference sites: W&B, Braintrust, PromptLayer, Linear, Vercel
- Locked Arctic Light color scheme (blue/teal, Fraunces + DM Sans + IBM Plex Mono)

### Architecture
- Finalized backend pipeline matching v2 flowchart exactly
- Decided: frontend-first with mock data, backend wired in later
- Decided: datasetless mode added — criteria builder + LLM-as-judge (no synthetic data gen for MVP)
- Simplified from 44 features → 14 essential features (removed: scorers page, datasets page, activity page, export page, ROUGE scorer, custom Python scorer, SSE streaming, keyboard nav, synthetic data gen)

### Documents Produced
| File | Status | Description |
|---|---|---|
| `roadmap.md` | ✅ Done | 14 features across 2 phases, build order, file structure |
| `prompt.md` | ✅ Done | 14 implementation prompts, one per feature, in build order |
| `progress.md` | ✅ This file | Session-by-session task tracker |
| UI prototype | ✅ Done | Full HTML prototype (`promptopt-v2.html`) — all 6 screens navigable |
| Backend flowchart v2 | ✅ Done | PDF exported, confirmed final architecture |

### UI Screens (HTML Prototype — not yet React)
| Screen | Status |
|---|---|
| Dashboard | ✅ Designed + built in prototype |
| Runs Table + Inspector | ✅ Designed + built in prototype |
| New Run Wizard | ✅ Designed + built in prototype |
| Prompt Registry | ✅ Designed + built in prototype |
| App Shell + Sidebar | ✅ Designed + built in prototype |

### GitHub
- Repository created: `deepthi-sm/PromptOpt-Automatic_Prompt_Optimization`
- Git confirmed installed at `C:\Program Files\Git\cmd\git.exe`
- VS Code confirmed installed (v1.117.0)
- Upload in progress via Command Prompt

---

## 🔄 In Progress

### GitHub Upload
- **Status:** Running commands in Command Prompt
- **Current step:** Cloning repo, copying files, pushing to main branch
- **Commands being run:**
  ```
  git clone https://github.com/deepthi-sm/PromptOpt-Automatic_Prompt_Optimization.git
  cd PromptOpt-Automatic_Prompt_Optimization
  copy roadmap.md .
  copy prompt.md .
  copy progress.md .
  git add .
  git commit -m "Add roadmap, prompt and progress files"
  git push -u origin main
  ```
- **Blocker:** Need Personal Access Token from `https://github.com/settings/tokens` for the push step

---

## ⏳ Pending

### Frontend (React — in build order)
| Task | Prompt | Status |
|---|---|---|
| F-01 Mock Data + api.js | P: F-01 | ⬜ Not started |
| F-02 App Shell + Routing | P: F-02 | ⬜ Not started |
| F-03 Dashboard | P: F-03 | ⬜ Not started |
| F-04 Runs Table + Inspector + Diff Viewer | P: F-04 | ⬜ Not started |
| F-05 New Run Wizard | P: F-05 | ⬜ Not started |
| F-06 Prompt Registry | P: F-06 | ⬜ Not started |

### Backend (FastAPI — in build order)
| Task | Prompt | Status |
|---|---|---|
| B-01 Job Initializer | P: B-01 | ⬜ Not started |
| B-02 Variant Generator | P: B-02 | ⬜ Not started |
| B-03 Dataset Scorer + Accuracy | P: B-03 | ⬜ Not started |
| B-04 Criteria Scorer | P: B-04 | ⬜ Not started |
| B-05 Score Collector + Optimizer Loop | P: B-05 | ⬜ Not started |
| B-06 Ranker + Best Prompt Store | P: B-06 | ⬜ Not started |
| B-07 Run API Endpoints | P: B-07 | ⬜ Not started |
| B-08 Export API | P: B-08 | ⬜ Not started |

### After Code Is Built
- [ ] Switch `VITE_DEMO_MODE=false` to wire frontend to real backend
- [ ] End-to-end test: create run → watch it optimize → export best prompt
- [ ] Push final code to GitHub under `main` branch

---

## 🔑 Key Context

### Architecture Decisions
| Decision | Choice | Reason |
|---|---|---|
| Theme | Arctic Light (light, blue/teal) | Better for professional/enterprise audience than dark terminal theme |
| Dataset | Optional — two modes supported | Key UX improvement — lower barrier to entry |
| Build order | Frontend first with mock data | Validate UI before committing to API shape |
| Streaming (SSE) | Removed for MVP | Polling every 3s is good enough; SSE adds complexity |
| Synthetic data gen | Removed for MVP | Adds backend complexity; criteria scorer works without it |
| ROUGE scorer | Removed | Accuracy + LLM judge covers 90% of use cases |
| Screen count | 4 screens (was 10) | Removed: scorers, datasets, activity, export as separate pages |
| Export | Folded into Registry | Simpler UX — export from the registry card directly |

### Final Feature List (14 total)
```
Frontend (6):              Backend (8):
F-01 Mock Data + api.js    B-01 Job Initializer
F-02 App Shell             B-02 Variant Generator
F-03 Dashboard             B-03 Dataset Scorer + Accuracy
F-04 Runs + Inspector      B-04 Criteria Scorer
F-05 New Run Wizard        B-05 Score Collector + Optimizer
F-06 Prompt Registry       B-06 Ranker + Best Prompt Store
                           B-07 Run API Endpoints
                           B-08 Export API
```

### Core Data Shapes (locked)
```js
// Run
{ id, task_name, task_type, mode, base_prompt, scorer,
  max_iterations, early_stop_threshold, variants_per_iter,
  status, best_score, baseline_score, best_prompt,
  iterations_run, token_count, latency_ms,
  failure_reason, created_at, completed_at }

// Variant
{ id, run_id, iteration, prompt_text, score,
  token_count, latency_ms, diff_tokens, created_at }

// Registry entry
{ id, task_name, task_type, mode, prompt_text,
  best_score, version, token_count, status, run_id, created_at }
```

### Stack (locked)
```
Frontend:  React + Vite · CSS variables · Recharts · React Router
Backend:   FastAPI · SQLite · Pydantic v2 · Anthropic SDK
Model:     claude-sonnet-4-5
Fonts:     Fraunces (headings) · DM Sans (body) · IBM Plex Mono (data)
```

### Deviations from Original Plan
| Original | Actual | Why |
|---|---|---|
| 44 features | 14 features | Too complex for MVP — cut everything non-essential |
| Dark terminal theme | Arctic Light (light) | Better readability, more professional |
| Dataset required | Dataset optional | Datasetless mode added for lower barrier to entry |
| Separate export page | Export in Registry | Simpler — one less screen |
| SSE streaming | Polling every 3s | SSE adds backend complexity without much UX gain |
| ROUGE scorer | Removed | Accuracy + LLM judge is sufficient |
| 10 UI screens | 4 screens | Removed non-core pages (activity, datasets, scorers) |
| Backend first | Frontend first | Faster to validate UX before API |

---

## 📁 Project File Structure (target)

```
PromptOpt-Automatic_Prompt_Optimization/
├── roadmap.md
├── prompt.md
├── progress.md
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

## 📊 Definition of Done (per feature)

- [ ] Works correctly with mock data (frontend) or passes unit tests (backend)
- [ ] No console errors
- [ ] Handles empty and error states
- [ ] Matches Arctic Light design system
- [ ] Pushed to `main` branch on GitHub

---

*Session 03 — Planning complete, GitHub upload in progress, coding not yet started*
*Next session: Start F-01 (mockData.js + api.js) using prompt block F-01 from prompt.md*
