# PromptOpt — Implementation Prompts
> One prompt per feature. Copy one block at a time into your coding tool.
> Never mix features in one session. Update progress.md after each.
> Version: 2.0 | Created: 2026-04-28

---

## Session Starter Context
> Paste this at the top of every new coding session before the feature prompt.

```
Project: PromptOpt — Automatic Prompt Optimization Platform
What it does: Iteratively improves LLM prompts via generate → score → converge → export loop
Two modes: dataset-guided (labeled examples) and datasetless (plain-English criteria rules)
Stack: React + Vite (frontend) · FastAPI + SQLite (backend) · Anthropic claude-sonnet-4-5

Design system — Arctic Light:
  Fonts: Fraunces (headings) · DM Sans (body/UI) · IBM Plex Mono (code/data/numbers)
  Colors:
    --bg:#f4f6f9  --bg2:#ffffff  --bg3:#eef1f6  --bg4:#e4e8f0
    --bd:#dde2ed  --bd2:#c8d0e0
    --t:#0d1424   --t2:#4a5568   --t3:#8896ac
    --ac:#1a6ef5  --ac2:#0f52c4
    --gr:#0d9e82  --grb:#e0f5f0
    --am:#d97706  --amb:#fef3e0
    --re:#dc2626  --reb:#fde8e8
    --bl:#2563eb  --blb:#e8f0fe
    --pu:#7c3aed  --pub:#f0ebfe
    --shadow: 0 1px 3px rgba(13,20,36,.08)
    --r:6px  --rl:10px

Build order:
  Frontend: F-01 mockData → F-02 App Shell → F-03 Dashboard →
            F-04 Runs+Inspector → F-05 Wizard → F-06 Registry
  Backend:  B-01 Job Init → B-02 Variant Gen → B-03 Scorer →
            B-04 Criteria → B-05 Optimizer → B-06 Ranker →
            B-07 Run API → B-08 Export API
```

---

## F-01 — Mock Data + api.js

**Files:** `src/lib/mockData.js` · `src/lib/api.js`
**Depends on:** nothing — build this first

---

Build two files that together make the entire React app runnable without any backend.

### mockData.js

Create realistic mock data matching exact API response shapes. Include:

**6 runs** covering all statuses:
```js
// Shape for every run object:
{
  id: "run-047",
  task_name: "Medical entity extraction",
  task_type: "extraction",        // classification|summarization|extraction|judge|generation
  mode: "dataset",                // dataset|nodataset
  base_prompt: "Extract all named entities from the following text...",
  scorer: "accuracy",             // accuracy|llm_judge
  max_iterations: 8,
  early_stop_threshold: 0.92,
  variants_per_iter: 5,
  status: "complete",             // queued|running|complete|failed
  best_score: 0.94,
  baseline_score: 0.71,
  best_prompt: "You are a precise medical assistant. Think step-by-step. Extract all named medical entities...",
  iterations_run: 5,
  token_count: 148,
  latency_ms: 312,
  failure_reason: null,
  created_at: "2026-04-28T09:14:02Z",
  completed_at: "2026-04-28T09:14:39Z"
}
```

Make these 6 runs:
1. `run-047` extraction, dataset, complete, score 0.94, 5/8 iters (early stop)
2. `run-048` classification, dataset, running, best so far 0.81, iter 3/8
3. `run-049` summarization, nodataset, running, best so far 0.67, iter 1/6
4. `run-046` summarization, dataset, complete, score 0.89, 4/6 iters
5. `run-045` judge, nodataset, complete, score 0.91, 6/6 iters
6. `run-044` classification, dataset, failed, failure_reason: "Dataset schema mismatch: label field missing"

**Prompt variants** — 5 per completed run (runs 047, 046, 045):
```js
{
  id: "run047-v3",
  run_id: "run-047",
  iteration: 3,
  prompt_text: "You are a precise medical assistant. Think step-by-step...",
  score: 0.84,
  token_count: 136,
  latency_ms: 298,
  diff_tokens: [
    { type: "equal", text: "You are a " },
    { type: "remove", text: "helpful" },
    { type: "add", text: "precise medical" },
    { type: "equal", text: " assistant. " },
    { type: "add", text: "Think step-by-step. " },
    { type: "equal", text: "Extract all " },
    { type: "remove", text: "relevant" },
    { type: "add", text: "named medical" },
    { type: "equal", text: " entities." }
  ],
  created_at: "2026-04-28T09:14:22Z"
}
```
Each run's 5 variants should show gradually increasing scores per iteration (e.g. 0.71 → 0.78 → 0.84 → 0.90 → 0.94).

**4 registry entries:**
```js
{
  id: "reg-001",
  task_name: "Medical entity extraction",
  task_type: "extraction",
  mode: "dataset",
  prompt_text: "You are a precise medical assistant. Think step-by-step...",
  best_score: 0.94,
  version: "v5",
  token_count: 148,
  status: "production",           // production|optimizing|draft
  run_id: "run-047",
  created_at: "2026-04-28T09:14:39Z"
}
```
Include: Medical NER (production), Toxicity judge nodataset (production), Sentiment classifier (optimizing), Email summarizer nodataset (draft).

**10 activity events:**
```js
{
  id: "evt-001",
  type: "run_complete",           // run_complete|run_started|iter_complete|early_stop|run_failed|prompt_saved
  message: "run-047 completed · score 0.94 · early stop at iter 5",
  run_id: "run-047",
  timestamp: "2026-04-28T09:14:39Z"
}
```

Export all collections plus a `mockApi` object:
```js
export const MOCK_RUNS = [...]
export const MOCK_VARIANTS = [...]
export const MOCK_REGISTRY = [...]
export const MOCK_ACTIVITY = [...]

const delay = (ms) => new Promise(r => setTimeout(r, ms))
const rand = (min, max) => Math.floor(min + Math.random() * (max - min))

export const mockApi = {
  getRuns: async (filters = {}) => {
    await delay(rand(300, 600))
    let runs = [...MOCK_RUNS]
    if (filters.status)    runs = runs.filter(r => r.status === filters.status)
    if (filters.mode)      runs = runs.filter(r => r.mode === filters.mode)
    if (filters.task_type) runs = runs.filter(r => r.task_type === filters.task_type)
    return runs
  },
  getRun:      async (id)     => { await delay(rand(200,400)); return MOCK_RUNS.find(r=>r.id===id)||null },
  getVariants: async (runId)  => { await delay(rand(200,400)); return MOCK_VARIANTS.filter(v=>v.run_id===runId) },
  createRun:   async (config) => { await delay(rand(600,1000)); return { id:`run-${Date.now()}`, ...config, status:'queued', created_at: new Date().toISOString() } },
  cancelRun:   async (id)     => { await delay(rand(200,400)); return { ok: true } },
  getRegistry: async (f={})   => { await delay(rand(300,600)); let r=[...MOCK_REGISTRY]; if(f.status) r=r.filter(x=>x.status===f.status); return r },
  saveToRegistry: async (runId) => { await delay(rand(400,700)); return { id:`reg-${Date.now()}`, run_id:runId } },
  exportRun:  async (id, fmt) => { await delay(rand(200,400)); const r=MOCK_RUNS.find(x=>x.id===id); return fmt==='json' ? r : r?.best_prompt },
  getVersions:async (runId)   => { await delay(rand(300,500)); return MOCK_VARIANTS.filter(v=>v.run_id===runId).sort((a,b)=>b.score-a.score) },
  getActivity:async ()        => { await delay(rand(200,400)); return [...MOCK_ACTIVITY] }
}

export const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'true'
```

### api.js

Single module. In demo mode, all calls route to mockApi. In production, calls fetch to FastAPI.

```js
import { mockApi, isDemoMode } from './mockData.js'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function req(method, path, body=null) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : null
  })
  if (!res.ok) {
    const err = await res.json().catch(()=>({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  getRuns:        (f)       => isDemoMode ? mockApi.getRuns(f)        : req('GET',    `/runs?${new URLSearchParams(f)}`),
  getRun:         (id)      => isDemoMode ? mockApi.getRun(id)         : req('GET',    `/runs/${id}`),
  getVariants:    (id)      => isDemoMode ? mockApi.getVariants(id)    : req('GET',    `/runs/${id}/variants`),
  createRun:      (c)       => isDemoMode ? mockApi.createRun(c)       : req('POST',   '/runs', c),
  cancelRun:      (id)      => isDemoMode ? mockApi.cancelRun(id)      : req('DELETE', `/runs/${id}`),
  getRegistry:    (f)       => isDemoMode ? mockApi.getRegistry(f)     : req('GET',    `/registry?${new URLSearchParams(f)}`),
  saveToRegistry: (runId)   => isDemoMode ? mockApi.saveToRegistry(runId): req('POST', '/registry', { run_id: runId }),
  exportRun:      (id, fmt) => isDemoMode ? mockApi.exportRun(id, fmt) : req('GET',    `/runs/${id}/export?format=${fmt}`),
  getVersions:    (id)      => isDemoMode ? mockApi.getVersions(id)    : req('GET',    `/runs/${id}/versions`),
  getActivity:    ()        => isDemoMode ? mockApi.getActivity()       : req('GET',    '/activity'),
}
```

**Acceptance criteria:**
- All 6 run statuses represented in mock data
- Mock functions accept same filter params as real API
- Data is internally consistent (variant run_ids match run ids)
- `isDemoMode` correctly reads env var
- All api functions return Promises in both modes

---

## F-02 — App Shell + Routing

**Files:** `App.jsx` · `Sidebar.jsx` · `design-system.css` · `main.jsx` · `index.html`
**Depends on:** F-01

---

Build the root layout, navigation sidebar, and React Router routing for all 4 pages.

### Setup

`index.html` — include Google Fonts in `<head>`:
```html
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=DM+Sans:wght@300;400;500;600&family=Fraunces:opsz,wght@9..144,300;9..144,600&display=swap" rel="stylesheet">
```

`design-system.css` — all CSS variables listed in the session context above, plus:
```css
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--sans); background: var(--bg); color: var(--t); height: 100vh; font-size: 13px; line-height: 1.5; overflow: hidden; }
.shell { display: flex; height: 100vh; }
```

`vite.config.js`:
```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({ plugins: [react()] })
```

`.env`:
```
VITE_DEMO_MODE=true
VITE_API_URL=http://localhost:8000
```

### Sidebar

Fixed 232px width, white background, right border. Structure:

```
Logo bar (18px 16px padding, bottom border):
  Blue square icon (30x30, border-radius 8px) with "P" in Fraunces
  "PromptOpt" in Fraunces 17px — "Opt" part in var(--ac)

Nav section "WORKSPACE" (10px mono label):
  ◈ Dashboard          → /
  ↻ Runs          [3]  → /runs     (badge: count of running runs)
  ✦ New Optimization   → /wizard

Nav section "LIBRARY":
  ≡ Prompt Registry    → /registry

Footer (auto margin-top, top border):
  Avatar circle (gradient ac→gr, initials "AK")
  Name: "Aryan Kumar" · Plan: "Pro · 847 runs"
```

Nav item styles:
- Default: `color: var(--t2)`, 13px DM Sans
- Hover: `background: var(--bg3)`, `color: var(--t)`
- Active: `background: rgba(26,110,245,.09)`, `color: var(--ac2)`, 2px left blue border via `::before`
- Use `useLocation()` to determine active route

Badge (run count): `background: var(--blb)`, `color: var(--bl)`, 10px mono, border-radius 10px

### App.jsx

```jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './components/Dashboard'
import RunsPage from './components/RunsPage'
import OptimizationWizard from './components/OptimizationWizard'
import PromptRegistry from './components/PromptRegistry'

export default function App() {
  return (
    <BrowserRouter>
      <div className="shell">
        <Sidebar />
        <main style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden', background:'var(--bg)' }}>
          <Routes>
            <Route path="/"         element={<Dashboard />} />
            <Route path="/runs"     element={<RunsPage />} />
            <Route path="/wizard"   element={<OptimizationWizard />} />
            <Route path="/registry" element={<PromptRegistry />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
```

### Reusable Topbar component

Used by every page. Place inside `components/Topbar.jsx`:
```jsx
export function Topbar({ title, children }) {
  return (
    <div style={{
      height:54, borderBottom:'1px solid var(--bd)',
      display:'flex', alignItems:'center', gap:12, padding:'0 22px',
      background:'var(--bg2)', flexShrink:0,
      boxShadow:'var(--shadow)'
    }}>
      <span style={{ fontFamily:'var(--disp)', fontSize:17, fontWeight:600, color:'var(--t)', letterSpacing:'-.3px' }}>{title}</span>
      <div style={{ marginLeft:'auto', display:'flex', gap:8, alignItems:'center' }}>{children}</div>
    </div>
  )
}
```

**Reusable Button component:**
```jsx
export function Btn({ variant='ghost', size='md', onClick, children }) {
  const base = { display:'inline-flex', alignItems:'center', gap:6, borderRadius:'var(--r)', fontFamily:'var(--sans)', cursor:'pointer', border:'1px solid transparent', fontWeight:500, transition:'all .15s' }
  const variants = {
    primary: { background:'var(--ac)', color:'#fff', borderColor:'var(--ac)', padding: size==='sm' ? '5px 11px' : '7px 14px', fontSize: size==='sm' ? 11.5 : 12.5 },
    ghost:   { background:'transparent', color:'var(--t2)', borderColor:'var(--bd2)', padding: size==='sm' ? '5px 11px' : '7px 14px', fontSize: size==='sm' ? 11.5 : 12.5 }
  }
  return <button style={{...base,...variants[variant]}} onClick={onClick}>{children}</button>
}
```

**Acceptance criteria:**
- All 4 routes render placeholder components without errors
- Active nav item correct for each route (use `useLocation`)
- Sidebar is exactly 232px, never collapses
- Badge shows count of running runs from mock data
- Google Fonts load correctly (check Network tab)

---

## F-03 — Dashboard

**File:** `components/Dashboard.jsx`
**Depends on:** F-01, F-02

---

Build the landing page. All data from `api.getRuns()` and `api.getActivity()`.

### Layout (flex column, gap 18px, padding 22px)
```
[4 stat cards — 4-column grid]
[Score chart — 1fr]   [Activity feed — 1fr]   (2-col grid)
[Active run cards — 3-col grid]
```

### Stat cards

Fetch runs once on mount. Compute all 4 values client-side:

```js
const completed = runs.filter(r => r.status === 'complete')
const running   = runs.filter(r => r.status === 'running')

const bestScore     = Math.max(...completed.map(r => r.best_score)).toFixed(2)
const activeRuns    = running.length
const avgImprovement = (completed.reduce((s,r) => s + (r.best_score - r.baseline_score), 0) / completed.length * 100).toFixed(0) + '%'
const totalVariants = runs.reduce((s,r) => s + (r.iterations_run * r.variants_per_iter), 0).toLocaleString()
```

Each card: white bg, 1px border, border-radius 10px, padding 16px 18px, box-shadow. 3px top border colored by type. Label in 11px mono uppercase `--t3`. Value in Fraunces 30px 600. Delta in 11.5px.

Colors: Best Score → `var(--gr)` · Active Runs → `var(--ac)` · Avg Improvement → `var(--am)` · Total Variants → `var(--pu)`

### Score chart

Use Recharts. Import: `LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip`

Data: completed runs sorted by `created_at`, mapped to `{ name: 'r1', score: 0.89 }`.

```jsx
<ResponsiveContainer width="100%" height={140}>
  <LineChart data={chartData} margin={{top:8,right:8,bottom:0,left:-16}}>
    <CartesianGrid stroke="var(--bd)" strokeDasharray="0" vertical={false}/>
    <XAxis dataKey="name" tick={{fontSize:9, fontFamily:'IBM Plex Mono', fill:'var(--t3)'}} axisLine={false} tickLine={false}/>
    <YAxis domain={['auto','auto']} tick={{fontSize:9, fontFamily:'IBM Plex Mono', fill:'var(--t3)'}} axisLine={false} tickLine={false}/>
    <Line type="monotone" dataKey="score" stroke="var(--gr)" strokeWidth={2}
      dot={{fill:'var(--gr)',r:3.5,strokeWidth:0}}
      activeDot={{r:5,fill:'var(--gr)',stroke:'#fff',strokeWidth:2}}/>
    <Tooltip contentStyle={{fontSize:12,fontFamily:'IBM Plex Mono',background:'var(--bg2)',border:'1px solid var(--bd)',borderRadius:6,boxShadow:'var(--shadow)'}} formatter={v=>[v.toFixed(2),'Score']}/>
  </LineChart>
</ResponsiveContainer>
```

Wrap in a card (white bg, border, border-radius 10px) with a card header showing "Score progression" title and filter chips (Score / Tokens — toggle which dataKey is shown).

### Activity feed

Fetch from `api.getActivity()`. Show 5 most recent events.

"Time ago" helper:
```js
function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso)) / 1000
  if (diff < 60)   return `${Math.floor(diff)}s ago`
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`
  if (diff < 86400)return `${Math.floor(diff/3600)}h ago`
  return `${Math.floor(diff/86400)}d ago`
}
```

Dot colors by event type:
```js
const DOT_COLOR = {
  run_complete:'var(--gr)', prompt_saved:'var(--gr)',
  run_started:'var(--ac)', iter_complete:'var(--ac)',
  early_stop:'var(--am)', run_failed:'var(--re)'
}
```

### Active run cards

Fetch running runs. One card per run (3-col grid, gap 14px). Each card:
- White bg, border, border-radius 10px, padding 16px
- 3px top border in `var(--ac)` for running, `var(--bd2)` for queued
- Row 1: Run ID (11px mono blue) + Status pill
- Row 2: Task name (13px 500)
- Row 3: Scorer + mode (11.5px grey)
- Progress bar: height 4px, `var(--bg4)` track, `var(--ac)` fill at `(iterations_run/max_iterations)*100`%
- Row 4: "best: {best_score}" left + "{pct}%" right (11px mono grey)

Status pill — running: `background: var(--blb)`, `color: var(--bl)`, 5px animated dot:
```css
@keyframes pls { 0%,100%{opacity:1} 50%{opacity:.35} }
```

"View all →" link at section header navigates to `/runs`.

**Acceptance criteria:**
- All 4 stat values computed correctly from mock data (not hardcoded)
- Chart renders all completed runs as data points
- Activity dots correctly colored by event type
- Progress bars show correct percentages
- Page has staggered fade-up animation on load

---

## F-04 — Runs Table + Inspector + Diff Viewer

**Files:** `components/RunsPage.jsx` · `components/RunInspector.jsx` · `src/lib/diff.js`
**Depends on:** F-01, F-02

---

Build the runs list with a docked inspector panel.

### diff.js

Implement word-level LCS diff:

```js
function tokenize(text) {
  return text.split(/(\s+)/).filter(Boolean)
}

function lcs(a, b) {
  const m=a.length, n=b.length
  const dp = Array.from({length:m+1}, ()=>new Array(n+1).fill(0))
  for(let i=1;i<=m;i++) for(let j=1;j<=n;j++)
    dp[i][j] = a[i-1]===b[j-1] ? dp[i-1][j-1]+1 : Math.max(dp[i-1][j],dp[i][j-1])
  return dp
}

function backtrack(dp, a, b) {
  const tokens=[]
  let i=a.length, j=b.length
  while(i>0||j>0) {
    if(i>0&&j>0&&a[i-1]===b[j-1]) { tokens.unshift({type:'equal',text:a[i-1]}); i--;j-- }
    else if(j>0&&(i===0||dp[i][j-1]>=dp[i-1][j])) { tokens.unshift({type:'add',text:b[j-1]}); j-- }
    else { tokens.unshift({type:'remove',text:a[i-1]}); i-- }
  }
  return tokens
}

export function computeDiff(baseText, optimizedText) {
  const a=tokenize(baseText), b=tokenize(optimizedText)
  return backtrack(lcs(a,b), a, b)
}
```

### RunsPage layout

```
[Topbar: "Optimization Runs"]  [↓ CSV]  [✦ New Run → /wizard]
[Tabs: All · Completed · Running · Failed]
─────────────────────────────────────────────────────────
[Table area — flex:1, overflow auto]    [RunInspector — 370px]
```

### Filter bar (above table)

```
[Search: "Search runs…"] [Chip:All✓] [Chip:With dataset] [Chip:No dataset]
                                                    [⇅ Sort]  [⊞ Columns]
```

Search filters `task_name` (case-insensitive, debounced 300ms).
Chips filter `mode`: "With dataset" → `mode==='dataset'`, "No dataset" → `mode==='nodataset'`.
Tabs filter `status`.

### Table

White bg card, border, border-radius 10px, `border-collapse: collapse`. Grey thead background (`var(--bg3)`), 11px mono uppercase column headers.

Columns:
- **Run** — `run-047` in 11px mono `var(--ac2)`
- **Task** — task_name in 13px 500 `var(--t)`
- **Type** — colored tag pill (see below)
- **Mode** — `dataset` in grey mono · `no dataset` in bold `var(--ac2)` mono
- **Score** — progress bar (80px, 5px height) + number (mono, green≥0.9, amber≥0.75, red<0.75)
- **Tokens** — mono grey
- **Iters** — `3/8` mono
- **Status** — pill
- **Time** — relative, grey

Task type tag colors:
```js
{ classification:'var(--blb)/#1e40af', summarization:'var(--pub)/#5b21b6',
  extraction:'var(--amb)/#92400e', judge:'var(--grb)/#065f46' }
```

Status pills:
```js
{ running:'var(--blb)/var(--bl)', complete:'var(--grb)/var(--gr)',
  failed:'var(--reb)/var(--re)', queued:'var(--bg4)/var(--t3)' }
```

Running pill has a pulsing 5px dot.

Row click: highlight row (`background: rgba(26,110,245,.06)`), load run into inspector.

Default sort: `created_at DESC`. Click column header → sort by that field, toggle ASC/DESC.

### RunInspector (370px right panel)

White bg, left border `var(--bd)`. Structure:

```
Header: "[run-047] · Inspector"    [↗ Full view]
Body (scrollable, padding 16px):
  METRICS (10px mono uppercase label)
  2×2 grid of metric boxes:
    Best score (var(--gr)) · Baseline · Tokens · Latency

  SCORE PER ITERATION
  SVG sparkline (hand-drawn, 320×54 viewBox)

  PROMPT DIFF · baseline → optimized
  DiffViewer (rendered diff tokens)

  RUN LOG
  Scrollable log area (max-height 180px)

  [↓ Export prompt]  [⊞ Save to registry]
```

Metric box: `background: var(--bg3)`, border, padding 9px 11px, flex space-between. Label 11px `--t3`, value 13px 600 mono `--t`.

SVG sparkline — compute from variant scores:
```jsx
function Sparkline({ variants }) {
  if (!variants.length) return null
  const sorted = [...variants].sort((a,b)=>a.iteration-b.iteration)
  const scores = sorted.map(v=>v.score)
  const W=320, H=54, PAD=18
  const min=Math.min(...scores)-0.03, max=Math.max(...scores)+0.02
  const pts = scores.map((s,i)=>({
    x: PAD+(i/(scores.length-1||1))*(W-PAD*2),
    y: H-PAD-((s-min)/(max-min||1))*(H-PAD*2)
  }))
  return (
    <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`}>
      <polyline points={pts.map(p=>`${p.x},${p.y}`).join(' ')} fill="none" stroke="var(--ac)" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"/>
      {pts.map((p,i)=>(
        <circle key={i} cx={p.x} cy={p.y}
          r={i===pts.length-1?4.5:3}
          fill={i===pts.length-1?'var(--gr)':'var(--ac)'}
          stroke={i===pts.length-1?'#fff':'none'} strokeWidth={2}/>
      ))}
      {pts.map((p,i)=>(
        <text key={i} x={p.x} y={H-2} textAnchor="middle" fill="var(--t3)" fontSize={9} fontFamily="IBM Plex Mono">i{i+1}</text>
      ))}
    </svg>
  )
}
```

DiffViewer — use `computeDiff(run.base_prompt, run.best_prompt)` and render tokens:
```jsx
function DiffViewer({ base, optimized }) {
  const tokens = useMemo(()=>computeDiff(base||'',optimized||''),[base,optimized])
  const [expanded,setExpanded] = useState(false)
  let chars=0, display=[]
  for(const t of tokens) {
    if(!expanded&&chars+t.text.length>800) break
    display.push(t); chars+=t.text.length
  }
  const styles = {
    add:    {background:'#d1fae5',color:'#065f46',borderRadius:3,padding:'1px 3px'},
    remove: {background:'#fee2e2',color:'#991b1b',borderRadius:3,padding:'1px 3px',textDecoration:'line-through'},
    equal:  {color:'var(--t2)'}
  }
  return (
    <div style={{background:'var(--bg3)',border:'1px solid var(--bd)',borderRadius:'var(--r)',padding:13,fontSize:12,lineHeight:1.9,fontFamily:'var(--mono)'}}>
      {display.map((t,i)=><span key={i} style={styles[t.type]}>{t.text}</span>)}
      {!expanded&&tokens.length>display.length&&(
        <button onClick={()=>setExpanded(true)} style={{marginLeft:6,fontSize:11,color:'var(--ac)',background:'none',border:'none',cursor:'pointer'}}>Show more</button>
      )}
    </div>
  )
}
```

Run log — show timestamped events with colored labels:
```
09:14:02  [INFO]   Job initialized
09:14:08  [SCORE]  iter-1: 0.71 (baseline)
09:14:39  [DONE]   Early stop · threshold exceeded
```
Generate these from the run's variant scores. `[INFO]`→blue, `[SCORE]`/`[DONE]`→green, `[ERROR]`→red. Max-height 180px, overflow-y auto, mono 11px.

When no run selected: show centered grey text "Select a run to inspect".

**Acceptance criteria:**
- Table sorts correctly on all columns
- Search debounced, updates in real-time
- Selected row highlighted, loads inspector
- Sparkline plots correctly per variant scores
- Diff highlights add/remove correctly
- Log scrolls independently

---

## F-05 — New Run Wizard

**File:** `components/OptimizationWizard.jsx`
**Depends on:** F-01, F-02

---

Build a 4-step guided form. Left sidebar (240px) shows step tracker. Right panel shows active step content.

### Layout
```
[Topbar: "New Optimization Run"]   [✕ Cancel]
[Content — 2-col grid: 240px steps | 1fr panel]
```

### Wizard state
```js
const [state, setState] = useState({
  taskName:'', taskType:'',
  basePrompt:'',
  mode:'dataset',           // 'dataset' | 'nodataset'
  dataset:[],               // [{input,label}]
  rawDatasetJson:'',
  datasetValid:false,
  criteria:[],              // string[]
  scorer:'',                // auto-set by mode
  maxIterations:8,
  earlyStopThreshold:0.92,
  variantsPerIter:5
})
const [step, setStep] = useState(1)
```

### Step tracker sidebar

Each step row: circle (24px) + title (12.5px 500) + subtitle (11.5px grey):
- Done: green circle `var(--grb)` + ✓, subtitle shows selection made
- Current: blue circle `var(--blb)` + number
- Todo: grey circle `var(--bg4)` + number

Steps:
1. Task Config — subtitle when done: e.g. "Sentiment · Classification"
2. Base Prompt — subtitle when done: e.g. "142 tokens · ready"
3. Dataset / Criteria — subtitle when done: e.g. "5 examples · accuracy" or "3 rules · LLM judge"
4. Run Config — subtitle when done: "8 iters · threshold 0.92"

### Step 1 — Task Config

```
Task name: [text input — required]
Task type: [select dropdown]
           Classification · Summarization · Extraction · Judge · Generation
```

"Next →" disabled until both fields filled.

### Step 2 — Base Prompt

```
[Textarea — mono, min-height 160px, placeholder: "Enter your starting prompt…"]
[Token counter: "142 / 4000 tokens"]  (estimate: Math.round(text.length/4))
[Hint: "This is your starting point. PromptOpt will improve it from here."]
```

Next disabled if empty or >4000 tokens.

### Step 3 — Dataset / Criteria

**Mode toggle** — two full-width cards side by side:
```
[📊 With dataset              ] [✏️ No dataset               ]
Labeled examples for           Define plain-English rules —
objective scoring              no examples needed
```
Active card: blue border `var(--ac)`, `background: var(--blb)`.

**With dataset** → JSON textarea:
```
[Textarea — mono, min-height 130px]
[Hint: "N examples loaded · JSON valid ✓" OR error message]
```
Validate on every change (debounced 200ms):
- Must be JSON array
- Each item needs `input: string` and `label: string`
- Green hint on valid, red error on invalid
- Show example format when empty

**No dataset** → Criteria builder:
```
SCORING CRITERIA
[Rule text                                           ] [×]
[Rule text                                           ] [×]
[Add a rule…                              ] [+ Add]
```
Rule items: `var(--bg3)` bg, border, padding 9px 12px. Remove `×`: hover turns red.
Enter key adds rule. Deduplicate. Min 1 rule.

Pre-suggest 2 starter rules based on `taskType`:
```js
const STARTERS = {
  classification:['Output must be exactly one class label','Never include reasoning — label only'],
  summarization: ['Summary must be 2-3 sentences maximum','Focus on action items only'],
  extraction:    ['Return output as a valid JSON array','Include only explicitly mentioned entities'],
  judge:         ['Return a float between 0.0 and 1.0 only','Do not include any explanation'],
  generation:    ['Stay strictly on topic','Use professional and concise tone']
}
```
Show as grey suggestion chips below the add input. Click to add as a rule.

Auto-set scorer based on mode:
- `dataset` → `scorer = 'accuracy'`
- `nodataset` → `scorer = 'llm_judge'`
Show as read-only info: "Scorer: Accuracy (auto-selected for dataset mode)"

Next disabled until: dataset valid with ≥1 example OR criteria has ≥1 rule.

### Step 4 — Run Config

```
Max iterations          [slider 2–20,    default 8]    [8]
Early stop threshold    [slider 0.5–1.0, default 0.92] [0.92]
Variants per iteration  [slider 2–10,    default 5]    [5]

Scorer: Accuracy  ← read-only display
```

Value display: 12.5px mono, `var(--ac2)`, right-aligned. Live update on slider input.

**Launch button** — full width, blue primary, `✦ Launch optimization run →`:
1. Assemble config object from `state`
2. Call `api.createRun(config)`
3. On success: navigate to `/runs`

**← Back** button navigates to previous step.

**Acceptance criteria:**
- Can't advance step until current step valid
- Done steps show correct summary subtitles
- Mode toggle shows/hides correct sub-form
- Criteria starter suggestions are clickable to add
- Sliders show live values
- Launch calls api and navigates to /runs

---

## F-06 — Prompt Registry

**File:** `components/PromptRegistry.jsx`
**Depends on:** F-01, F-02

---

Build the saved prompt library with export and re-optimize actions.

### Layout
```
[Topbar: "Prompt Registry"]   [✦ New prompt]
[Tabs: All · Production · Optimizing · Draft]
[Filter bar: search + chips]
[2-column card grid, gap 14px]
```

### Card structure

White bg, 1px border, border-radius 10px, box-shadow. Three sections:

**Header** (padding 14px 16px, bottom border):
- Left: task name (13.5px 500 `--t`), mode label below (11.5px grey; "no dataset" in bold `var(--ac2)`)
- Right: status pill

**Body** (padding 14px 16px, flex column gap 10px):
- Prompt preview box: mono 11.5px, `var(--bg3)` bg, border, padding 10px 12px, `-webkit-line-clamp: 3`
- Metrics row: Score (green if production) · Version (mono blue) · Tokens + Type tag (right-aligned)

**Footer** (padding 12px 16px, `var(--bg3)` bg, top border, flex row):
- `↓ Export` ghost button
- `⊞ History` ghost button
- `↻ Re-optimize` primary button (right-aligned, margin-left auto)
- For `status==='optimizing'`: replace re-optimize with `✕ Stop run` in danger style (red text, red-bg)

### Status pills
```
production → var(--grb) bg · var(--gr) text
optimizing → var(--blb) bg · var(--bl) text + pulse dot
draft      → var(--bg4) bg · var(--t3) text
```

### Tabs

Filter by status. Show count in "All (12)" format. Active tab: bottom border `var(--ac)`, color `var(--ac2)`.

### Filter chips

All types · With dataset (`mode==='dataset'`) · No dataset (`mode==='nodataset'`)

### Export (↓)

Download the `prompt_text` as a `.txt` file:
```js
function downloadText(text, name) {
  const blob = new Blob([text], {type:'text/plain'})
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href=url; a.download=`${name.replace(/\s+/g,'-').toLowerCase()}.txt`; a.click()
  URL.revokeObjectURL(url)
}
```

### History drawer (⊞)

State: `drawerOpen: bool`, `drawerEntry: registryItem`

Slide-in panel from right (position absolute/fixed is fine here since it overlays the card grid, not the whole page). Width 360px. Shows:

```
Version History — {task_name}
──────────────────────────────────────
[v5]  Optimized · iter 5 · early stop   0.94   2m ago
[v4]  Optimized · iter 4                0.90   2d ago
[v3]  Optimized · iter 6                0.86   5d ago
[v1]  Baseline · manual                 0.71   2w ago
```

Fetch from `api.getVersions(entry.run_id)`. Latest version badge: blue bg. Older: grey bg. Score: green for max, grey for rest. Click row → update displayed prompt preview in the drawer. ESC or ✕ closes.

### Re-optimize (↻)

Navigate to `/wizard` passing the entry's `prompt_text` as state:
```js
navigate('/wizard', { state: { prefillPrompt: entry.prompt_text, prefillTaskType: entry.task_type } })
```
In wizard Step 2, check for `location.state?.prefillPrompt` and pre-fill the textarea.

**Acceptance criteria:**
- 2-col card grid renders all 4 mock registry entries
- Tabs filter correctly (show count in All tab)
- Export downloads .txt file with prompt text
- History drawer opens/closes, shows version list
- Re-optimize navigates to wizard with prompt pre-filled
- Production and Optimizing status pills display correctly

---

## B-01 — Job Initializer

**File:** `backend/core/job_initializer.py` · `backend/db/models.py` · `backend/db/database.py`
**Depends on:** nothing — first backend feature

---

Build the config validator and run persistence layer.

```python
# backend/db/database.py
import sqlite3

DB_PATH = "promptopt.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS runs (
        id                    TEXT PRIMARY KEY,
        task_name             TEXT NOT NULL,
        task_type             TEXT NOT NULL,
        mode                  TEXT NOT NULL,
        base_prompt           TEXT NOT NULL,
        scorer                TEXT NOT NULL,
        max_iterations        INTEGER NOT NULL DEFAULT 8,
        early_stop_threshold  REAL NOT NULL DEFAULT 0.92,
        variants_per_iter     INTEGER NOT NULL DEFAULT 5,
        dataset_json          TEXT,
        criteria_json         TEXT,
        status                TEXT NOT NULL DEFAULT 'queued',
        best_score            REAL,
        baseline_score        REAL,
        best_prompt           TEXT,
        iterations_run        INTEGER DEFAULT 0,
        token_count           INTEGER,
        latency_ms            INTEGER,
        failure_reason        TEXT,
        created_at            TEXT NOT NULL,
        completed_at          TEXT
    );

    CREATE TABLE IF NOT EXISTS prompt_variants (
        id           TEXT PRIMARY KEY,
        run_id       TEXT NOT NULL,
        iteration    INTEGER NOT NULL,
        prompt_text  TEXT NOT NULL,
        score        REAL,
        token_count  INTEGER,
        latency_ms   INTEGER,
        diff_json    TEXT,
        created_at   TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES runs(id)
    );
    """)
    conn.commit()
    conn.close()
```

```python
# backend/core/job_initializer.py
from pydantic import BaseModel, validator, Field
from typing import Optional
from enum import Enum
import uuid, json
from datetime import datetime, timezone
from ..db.database import get_db

class TaskType(str, Enum):
    classification = "classification"
    summarization  = "summarization"
    extraction     = "extraction"
    judge          = "judge"
    generation     = "generation"

class Mode(str, Enum):
    dataset   = "dataset"
    nodataset = "nodataset"

class ScorerType(str, Enum):
    accuracy  = "accuracy"
    llm_judge = "llm_judge"

class DatasetExample(BaseModel):
    input: str
    label: str

class CriteriaRule(BaseModel):
    text: str

class RunConfig(BaseModel):
    task_name:            str   = Field(..., min_length=1, max_length=200)
    task_type:            TaskType
    mode:                 Mode
    base_prompt:          str   = Field(..., min_length=1, max_length=16000)
    scorer:               ScorerType
    max_iterations:       int   = Field(8,    ge=2, le=20)
    early_stop_threshold: float = Field(0.92, ge=0.5, le=1.0)
    variants_per_iter:    int   = Field(5,    ge=2, le=10)
    dataset:  Optional[list[DatasetExample]] = None
    criteria: Optional[list[CriteriaRule]]   = None

    @validator('dataset')
    def validate_dataset(cls, v, values):
        if values.get('mode') == Mode.dataset:
            if not v or len(v) == 0:
                raise ValueError('dataset required and must be non-empty when mode is "dataset"')
        return v

    @validator('criteria')
    def validate_criteria(cls, v, values):
        if values.get('mode') == Mode.nodataset:
            if not v or len(v) == 0:
                raise ValueError('at least one criteria rule required when mode is "nodataset"')
        return v

    @validator('scorer')
    def validate_scorer(cls, v, values):
        if values.get('mode') == Mode.nodataset and v == ScorerType.accuracy:
            raise ValueError('accuracy scorer requires dataset mode')
        return v

def create_run(config: RunConfig) -> dict:
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    conn.execute("""
        INSERT INTO runs
        (id,task_name,task_type,mode,base_prompt,scorer,
         max_iterations,early_stop_threshold,variants_per_iter,
         dataset_json,criteria_json,status,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        run_id, config.task_name, config.task_type.value, config.mode.value,
        config.base_prompt, config.scorer.value,
        config.max_iterations, config.early_stop_threshold, config.variants_per_iter,
        json.dumps([e.dict() for e in config.dataset]) if config.dataset else None,
        json.dumps([r.dict() for r in config.criteria]) if config.criteria else None,
        'queued', now
    ))
    conn.commit()
    conn.close()
    return {'id': run_id, 'status': 'queued', 'created_at': now}
```

Write these 4 unit tests:
1. Valid dataset run creates record and returns run_id
2. Empty dataset in dataset mode raises ValidationError
3. Empty criteria in nodataset mode raises ValidationError
4. Accuracy scorer in nodataset mode raises ValidationError

**Acceptance criteria:** All 4 tests pass · DB file created on first run · run_id format `run-{8hex}`

---

## B-02 — Variant Generator

**File:** `backend/core/variant_generator.py`
**Depends on:** B-01

---

Call the Anthropic API to generate N improved prompt variants.

```python
import anthropic, json, time
from typing import Optional

client = anthropic.Anthropic()

META_PROMPTS = {
    "classification": """You are an expert prompt engineer for text classification tasks.

Current prompt: <prompt>{prompt}</prompt>
Current weaknesses: {feedback}
Task: {task_name}

Generate {n} improved versions. Each must:
- State expected output labels explicitly
- Add clear format instructions
- Use unambiguous, direct language

Return ONLY a JSON array of {n} strings. No preamble, no explanation.""",

    "summarization": """You are an expert prompt engineer for text summarization.

Current prompt: <prompt>{prompt}</prompt>
Current weaknesses: {feedback}
Task: {task_name}

Generate {n} improved versions. Each must:
- Specify output length and format
- Define what to include and exclude
- Clarify the target audience/tone

Return ONLY a JSON array of {n} strings. No preamble.""",

    "extraction": """You are an expert prompt engineer for information extraction.

Current prompt: <prompt>{prompt}</prompt>
Current weaknesses: {feedback}
Task: {task_name}

Generate {n} improved versions. Each must:
- Specify exact output format (JSON preferred)
- Name entity types to extract
- Handle edge cases (none found, ambiguous)

Return ONLY a JSON array of {n} strings. No preamble.""",

    "judge": """You are an expert prompt engineer for LLM evaluation tasks.

Current prompt: <prompt>{prompt}</prompt>
Current weaknesses: {feedback}
Task: {task_name}

Generate {n} improved versions. Each must:
- Define evaluation criteria clearly
- Specify output format (single float or JSON)
- Include scoring scale and anchors

Return ONLY a JSON array of {n} strings. No preamble.""",

    "generation": """You are an expert prompt engineer for text generation tasks.

Current prompt: <prompt>{prompt}</prompt>
Current weaknesses: {feedback}
Task: {task_name}

Generate {n} improved versions. Each must:
- Clarify tone, length, and constraints
- Specify what to avoid
- Include output format if needed

Return ONLY a JSON array of {n} strings. No preamble."""
}

def generate_variants(
    prompt: str,
    task_type: str,
    task_name: str,
    n_variants: int,
    feedback: Optional[str] = None
) -> list[str]:
    fb = feedback or "No specific issues yet. Focus on clarity, specificity, and format instructions."
    template = META_PROMPTS.get(task_type, META_PROMPTS["generation"])
    user_msg = template.format(prompt=prompt, feedback=fb, task_name=task_name, n=n_variants)

    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                messages=[{"role": "user", "content": user_msg}]
            )
            raw = response.content[0].text.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:-1])
            variants = json.loads(raw)
            if not isinstance(variants, list):
                raise ValueError("Not a JSON array")
            # Clean and deduplicate
            seen, unique = set(), []
            for v in variants:
                if isinstance(v, str) and v.strip() and v.strip() not in seen:
                    seen.add(v.strip())
                    unique.append(v.strip())
            # Pad if too few
            while len(unique) < n_variants:
                unique.append(prompt)
            return unique[:n_variants]
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"Variant generation failed after 3 attempts: {e}")
            time.sleep(2 ** attempt)
```

**Acceptance criteria:** Returns exactly N strings · Retries 3× with backoff · Deduplicates · Strips markdown fences from response

---

## B-03 — Dataset Scorer + Accuracy Evaluator

**File:** `backend/core/scorer.py`
**Depends on:** B-01

---

Run variants against labeled examples and score results.

```python
import asyncio, anthropic
from typing import Optional

client = anthropic.Anthropic()

async def run_single(variant: str, example: dict, timeout: float = 10.0) -> dict:
    """Run one variant on one dataset example."""
    prompt = f"{variant}\n\nInput: {example['input']}"
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.messages.create,
                model="claude-sonnet-4-5",
                max_tokens=256,
                messages=[{"role":"user","content":prompt}]
            ),
            timeout=timeout
        )
        output = response.content[0].text.strip()
    except asyncio.TimeoutError:
        output = ""
    except Exception:
        output = ""
    return {"input": example["input"], "label": example["label"], "model_output": output}

async def run_on_dataset(variant: str, dataset: list[dict]) -> list[dict]:
    """Run variant on all dataset examples, up to 5 in parallel."""
    results = []
    for i in range(0, len(dataset), 5):
        batch = dataset[i:i+5]
        batch_results = await asyncio.gather(*[run_single(variant, ex) for ex in batch])
        results.extend(batch_results)
    return results

def match_label(output: str, label: str) -> bool:
    """Three-tier case-insensitive matching."""
    o, l = output.lower().strip(), label.lower().strip()
    if o == l: return True                           # exact match
    if l in o: return True                           # substring match
    if o.split()[0] == l if o.split() else False: return True  # first-word match
    return False

def accuracy_score(scored_outputs: list[dict]) -> float:
    """Compute accuracy from scored outputs."""
    if not scored_outputs:
        return 0.0
    correct = sum(1 for o in scored_outputs if match_label(o["model_output"], o["label"]))
    return round(correct / len(scored_outputs), 4)

async def llm_judge_score(variant: str, task_type: str, outputs: list[str]) -> float:
    """Ask LLM to rate output quality. Used for nodataset mode."""
    if not outputs:
        return 0.0
    scores = []
    for output in outputs[:5]:  # cap at 5 to control cost
        judge_prompt = f"""Rate the quality of this output for a {task_type} task on a scale of 0.0 to 1.0.

Task prompt: {variant[:500]}
Output: {output[:500]}

Respond ONLY with a JSON object: {{"score": 0.0, "reason": "brief reason"}}"""
        try:
            response = await asyncio.to_thread(
                client.messages.create,
                model="claude-sonnet-4-5",
                max_tokens=100,
                messages=[{"role":"user","content":judge_prompt}]
            )
            import json
            data = json.loads(response.content[0].text.strip())
            s = float(data.get("score", 0))
            scores.append(max(0.0, min(1.0, s)))
        except Exception:
            scores.append(0.0)
    return round(sum(scores) / len(scores), 4) if scores else 0.0
```

**Acceptance criteria:** Parallel batching works · Timeout per example · Three-tier matching tested with known inputs

---

## B-04 — Criteria Scorer

**File:** `backend/core/criteria_scorer.py`
**Depends on:** B-01

---

Score a variant against plain-English criteria rules.

```python
import asyncio, anthropic, json
from dataclasses import dataclass

client = anthropic.Anthropic()

GENERIC_TEST_INPUTS = {
    "classification": "This product is absolutely amazing and exceeded all my expectations.",
    "summarization":  "Hi team, following up on yesterday's meeting. We agreed to push the launch date to Q3. Sarah will lead the redesign. Budget approved at $50k. Please confirm receipt.",
    "extraction":     "Patient John Doe, 45, presented with type 2 diabetes and hypertension. Prescribed metformin 500mg twice daily.",
    "judge":          "The capital of France is Paris. It has been the capital since the 10th century.",
    "generation":     "Write a professional email declining a meeting invitation."
}

@dataclass
class RuleResult:
    rule: str
    passed: bool
    reason: str

async def check_rule(output: str, rule: str) -> RuleResult:
    """Ask LLM to judge whether output satisfies one rule."""
    prompt = f"""Does this output satisfy the rule?

Rule: "{rule}"
Output: "{output[:600]}"

Answer with exactly this JSON: {{"passed": true/false, "reason": "one sentence"}}"""
    try:
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-5",
            max_tokens=80,
            messages=[{"role":"user","content":prompt}]
        )
        data = json.loads(response.content[0].text.strip())
        return RuleResult(rule=rule, passed=bool(data.get("passed")), reason=data.get("reason",""))
    except Exception:
        return RuleResult(rule=rule, passed=False, reason="Evaluation failed")

async def get_variant_output(variant: str, test_input: str) -> str:
    """Run the variant on a test input to get its output."""
    try:
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-5",
            max_tokens=512,
            messages=[{"role":"user","content":f"{variant}\n\nInput: {test_input}"}]
        )
        return response.content[0].text.strip()
    except Exception:
        return ""

async def criteria_score(variant: str, criteria: list[str], task_type: str, test_input: str | None = None) -> dict:
    """Score a variant against all criteria rules. Returns score and per-rule detail."""
    if not criteria:
        return {"score": 0.0, "rule_results": []}

    input_to_use = test_input or GENERIC_TEST_INPUTS.get(task_type, "Test input")
    output = await get_variant_output(variant, input_to_use)

    if not output:
        return {"score": 0.0, "rule_results": [{"rule":r,"passed":False,"reason":"No output generated"} for r in criteria]}

    rule_results = await asyncio.gather(*[check_rule(output, rule) for rule in criteria])
    passed = sum(1 for r in rule_results if r.passed)
    score = round(passed / len(criteria), 4)

    return {
        "score": score,
        "rule_results": [{"rule":r.rule,"passed":r.passed,"reason":r.reason} for r in rule_results]
    }
```

**Acceptance criteria:** All rules checked in parallel · Generic test input used when none provided · Returns per-rule detail for UI display

---

## B-05 — Score Collector + Convergence Check + Optimizer Loop

**File:** `backend/core/optimizer.py`
**Depends on:** B-01, B-02, B-03, B-04

---

The main optimization loop that orchestrates everything.

```python
import asyncio, json, time
from datetime import datetime, timezone
from .job_initializer import RunConfig
from .variant_generator import generate_variants
from .scorer import run_on_dataset, accuracy_score, llm_judge_score
from .criteria_scorer import criteria_score
from ..db.database import get_db

def normalise_score(raw: float, scorer_type: str) -> float:
    """Clip score to [0, 1]. All current scorers already return 0–1."""
    return max(0.0, min(1.0, float(raw)))

def check_convergence(
    best_score: float,
    threshold: float,
    iterations_run: int,
    max_iterations: int,
    score_history: list[float]
) -> tuple[bool, str]:
    if best_score >= threshold:
        return True, "threshold_met"
    if iterations_run >= max_iterations:
        return True, "max_iterations"
    if len(score_history) >= 3:
        last3 = score_history[-3:]
        if max(last3) - min(last3) < 0.005:
            return True, "no_improvement"
    return False, ""

def update_run(run_id: str, **kwargs):
    conn = get_db()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    conn.execute(f"UPDATE runs SET {sets} WHERE id=?", [*kwargs.values(), run_id])
    conn.commit()
    conn.close()

def save_variant(run_id: str, iteration: int, prompt: str, score: float, token_count: int, latency_ms: int):
    import uuid
    conn = get_db()
    conn.execute("""
        INSERT INTO prompt_variants (id,run_id,iteration,prompt_text,score,token_count,latency_ms,created_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, (f"{run_id}-i{iteration}", run_id, iteration, prompt, score, token_count, latency_ms,
          datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()

async def score_variant(prompt: str, config: dict, mode: str, scorer: str) -> float:
    """Score one variant based on mode and scorer type."""
    if mode == "dataset":
        dataset = json.loads(config["dataset_json"])
        outputs = await run_on_dataset(prompt, dataset)
        if scorer == "accuracy":
            return accuracy_score(outputs)
        else:  # llm_judge
            raw_outputs = [o["model_output"] for o in outputs]
            return await llm_judge_score(prompt, config["task_type"], raw_outputs)
    else:  # nodataset
        criteria = [r["text"] for r in json.loads(config["criteria_json"])]
        result = await criteria_score(prompt, criteria, config["task_type"])
        return result["score"]

async def run_optimization(run_id: str):
    """Main optimization loop."""
    conn = get_db()
    row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    conn.close()
    if not row:
        return
    config = dict(row)

    try:
        update_run(run_id, status="running")

        # Score baseline
        baseline_score = await score_variant(config["base_prompt"], config, config["mode"], config["scorer"])
        baseline_score = normalise_score(baseline_score, config["scorer"])
        update_run(run_id, baseline_score=baseline_score)

        current_best_prompt = config["base_prompt"]
        current_best_score  = baseline_score
        score_history       = [baseline_score]
        feedback            = None

        for iteration in range(1, config["max_iterations"] + 1):
            # Generate variants
            variants = generate_variants(
                current_best_prompt, config["task_type"], config["task_name"],
                config["variants_per_iter"], feedback
            )

            # Score all variants
            scored = []
            for v in variants:
                t0 = time.time()
                s = await score_variant(v, config, config["mode"], config["scorer"])
                s = normalise_score(s, config["scorer"])
                latency = int((time.time()-t0)*1000)
                token_count = len(v.split())
                scored.append({"prompt":v, "score":s, "latency":latency, "tokens":token_count})
                save_variant(run_id, iteration, v, s, token_count, latency)

            # Find best this iteration
            best_this_iter = max(scored, key=lambda x: x["score"])
            if best_this_iter["score"] > current_best_score:
                current_best_score  = best_this_iter["score"]
                current_best_prompt = best_this_iter["prompt"]
                feedback = None
            else:
                feedback = f"Score did not improve (best was {current_best_score:.3f}). Try more aggressive changes."

            score_history.append(current_best_score)
            update_run(run_id, iterations_run=iteration, best_score=current_best_score, best_prompt=current_best_prompt)

            # Check convergence
            converged, reason = check_convergence(
                current_best_score, config["early_stop_threshold"],
                iteration, config["max_iterations"], score_history
            )
            if converged:
                break

        # Final update
        update_run(run_id,
            status="complete",
            best_prompt=current_best_prompt,
            best_score=current_best_score,
            completed_at=datetime.now(timezone.utc).isoformat()
        )

    except Exception as e:
        update_run(run_id, status="failed", failure_reason=str(e))
```

**Acceptance criteria:** Status transitions queued→running→complete/failed · Baseline scored before loop · All variants saved to DB · Convergence stops loop correctly

---

## B-06 — Ranker + Best Prompt Store

**File:** `backend/core/ranker.py`
**Depends on:** B-05

---

Sort variants and persist the winner. This is called at the end of `run_optimization` — add these functions to `optimizer.py` or a separate `ranker.py`.

```python
# backend/core/ranker.py
from ..db.database import get_db

def rank_variants(variants: list[dict]) -> list[dict]:
    """Sort by: score DESC → token_count ASC → latency_ms ASC"""
    return sorted(
        variants,
        key=lambda v: (-v.get("score",0), v.get("token_count",9999), v.get("latency_ms",9999))
    )

def get_all_variants(run_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM prompt_variants WHERE run_id=? ORDER BY score DESC",
        (run_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def store_best(run_id: str) -> dict | None:
    """Rank all variants and update run record with winner."""
    variants = get_all_variants(run_id)
    if not variants:
        return None
    ranked = rank_variants(variants)
    best = ranked[0]
    conn = get_db()
    from datetime import datetime, timezone
    conn.execute("""
        UPDATE runs SET
          best_prompt=?, best_score=?, token_count=?, latency_ms=?,
          status='complete', completed_at=?
        WHERE id=?
    """, (best["prompt_text"], best["score"], best["token_count"],
          best["latency_ms"], datetime.now(timezone.utc).isoformat(), run_id))
    conn.commit()
    conn.close()
    return best
```

**Acceptance criteria:** Sort order correct (score desc, tokens asc, latency asc) · Run record updated with winner's data

---

## B-07 — Run API Endpoints

**Files:** `backend/routers/runs.py` · `backend/main.py`
**Depends on:** B-01 through B-06

---

```python
# backend/routers/runs.py
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from typing import Optional
from ..core.job_initializer import RunConfig, create_run
from ..core.optimizer import run_optimization
from ..db.database import get_db

router = APIRouter(prefix="/runs", tags=["runs"])

@router.post("", status_code=201)
async def create_run_endpoint(config: RunConfig, background_tasks: BackgroundTasks):
    run = create_run(config)
    background_tasks.add_task(run_optimization, run["id"])
    return run

@router.get("")
async def list_runs(
    status:    Optional[str] = Query(None),
    mode:      Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    conn = get_db()
    q, p = "SELECT * FROM runs WHERE 1=1", []
    if status:    q += " AND status=?";    p.append(status)
    if mode:      q += " AND mode=?";      p.append(mode)
    if task_type: q += " AND task_type=?"; p.append(task_type)
    q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    p += [page_size, (page-1)*page_size]
    rows = conn.execute(q, p).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/{run_id}")
async def get_run(run_id: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    conn.close()
    if not row: raise HTTPException(404, "Run not found")
    return dict(row)

@router.delete("/{run_id}", status_code=204)
async def cancel_run(run_id: str):
    conn = get_db()
    row = conn.execute("SELECT status FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row: raise HTTPException(404, "Run not found")
    if row["status"] not in ("queued","running"):
        raise HTTPException(400, f"Cannot cancel run with status '{row['status']}'")
    conn.execute("UPDATE runs SET status='failed', failure_reason='Cancelled by user' WHERE id=?", (run_id,))
    conn.commit()
    conn.close()

@router.get("/{run_id}/variants")
async def get_variants(run_id: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM prompt_variants WHERE run_id=? ORDER BY iteration, score DESC",
        (run_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.runs import router as runs_router
from .routers.export import router as export_router
from .db.database import init_db

app = FastAPI(title="PromptOpt API", version="1.0")

app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
def startup():
    init_db()

app.include_router(runs_router)
app.include_router(export_router)

@app.get("/health")
def health():
    return {"status": "ok"}
```

```
# requirements.txt
fastapi>=0.110
uvicorn[standard]>=0.27
pydantic>=2.0
anthropic>=0.25
python-multipart>=0.0.9
```

**Acceptance criteria:** `POST /runs` returns 201 + starts background task · `GET /runs` filters work · `GET /runs/{id}` returns 404 for unknown IDs · `DELETE` returns 400 for already-complete runs · CORS allows localhost:5173

---

## B-08 — Export API

**File:** `backend/routers/export.py`
**Depends on:** B-07

---

```python
# backend/routers/export.py
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from datetime import datetime, timezone
from ..db.database import get_db

router = APIRouter(tags=["export"])

# ── Export endpoints ──────────────────────────────────

@router.get("/runs/{run_id}/export")
async def export_run(run_id: str, format: str = Query("text", regex="^(text|json)$")):
    conn = get_db()
    row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    conn.close()
    if not row: raise HTTPException(404, "Run not found")
    run = dict(row)
    if not run.get("best_prompt"): raise HTTPException(400, "Run has no best prompt yet")

    if format == "text":
        return PlainTextResponse(run["best_prompt"])

    return {
        "prompt":      run["best_prompt"],
        "score":       run["best_score"],
        "token_count": run["token_count"],
        "latency_ms":  run["latency_ms"],
        "run_id":      run_id,
        "task_name":   run["task_name"],
        "task_type":   run["task_type"],
        "mode":        run["mode"],
        "created_at":  run["completed_at"]
    }

@router.get("/runs/{run_id}/versions")
async def get_versions(run_id: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM prompt_variants WHERE run_id=? ORDER BY score DESC",
        (run_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Registry endpoints ────────────────────────────────

@router.post("/registry", status_code=201)
async def save_to_registry(body: dict):
    run_id = body.get("run_id")
    if not run_id: raise HTTPException(400, "run_id required")
    conn = get_db()
    run = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not run: raise HTTPException(404, "Run not found")
    if not dict(run).get("best_prompt"): raise HTTPException(400, "Run not complete")
    import uuid
    reg_id = f"reg-{uuid.uuid4().hex[:8]}"
    run = dict(run)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS registry (
            id TEXT PRIMARY KEY, task_name TEXT, task_type TEXT, mode TEXT,
            prompt_text TEXT, best_score REAL, version TEXT, token_count INTEGER,
            status TEXT DEFAULT 'production', run_id TEXT, created_at TEXT
        )
    """)
    version_num = conn.execute("SELECT COUNT(*) FROM registry WHERE run_id=?", (run_id,)).fetchone()[0] + 1
    conn.execute("""
        INSERT INTO registry (id,task_name,task_type,mode,prompt_text,best_score,version,token_count,status,run_id,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (reg_id, run["task_name"], run["task_type"], run["mode"], run["best_prompt"],
          run["best_score"], f"v{version_num}", run["token_count"],
          "production", run_id, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()
    return {"id": reg_id, "version": f"v{version_num}"}

@router.get("/registry")
async def list_registry(status: str = Query(None)):
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS registry (
            id TEXT PRIMARY KEY, task_name TEXT, task_type TEXT, mode TEXT,
            prompt_text TEXT, best_score REAL, version TEXT, token_count INTEGER,
            status TEXT DEFAULT 'production', run_id TEXT, created_at TEXT
        )
    """)
    q, p = "SELECT * FROM registry WHERE 1=1", []
    if status: q += " AND status=?"; p.append(status)
    q += " ORDER BY created_at DESC"
    rows = conn.execute(q, p).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.patch("/registry/{reg_id}")
async def update_registry(reg_id: str, body: dict):
    allowed = {"status"}
    updates = {k:v for k,v in body.items() if k in allowed}
    if not updates: raise HTTPException(400, "No valid fields to update")
    conn = get_db()
    sets = ", ".join(f"{k}=?" for k in updates)
    conn.execute(f"UPDATE registry SET {sets} WHERE id=?", [*updates.values(), reg_id])
    conn.commit()
    conn.close()
    return {"ok": True}
```

**Acceptance criteria:** `/export?format=text` returns plain string · `/export?format=json` returns full metadata object · `/registry` CRUD works · Registry table auto-created if missing · 400 returned when run not complete

---

*prompt.md v2.0 — PromptOpt simplified · 14 features · 2026-04-28*
*One prompt per session. Never mix features. Update progress.md after each.*
