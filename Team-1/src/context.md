# context.md — ACE-Powered Text-to-SQL Agent

## Project Title
**Self-Improving Text-to-SQL Agent via Agentic Context Engineering (ACE)**
Model: `qwen2.5-coder` via Ollama | Dataset: BIRD Benchmark

---

## Core Research Papers

### 1. ACE — Agentic Context Engineering (arXiv: 2510.04618)
**Zhang et al., Stanford / SambaNova — ICLR 2026**

ACE improves LLM performance by evolving what goes *into* the context — not the model weights.

**Two failure modes ACE fixes:**
- *Brevity bias*: Prompt optimisers compress context into short generic instructions, losing domain-specific detail. GEPA collapses to "Create unit tests to ensure methods behave as expected" — same prompt every iteration, domain diversity lost.
- *Context collapse*: Monolithic rewriting causes accumulated knowledge to be compressed away. At step 60 on AppWorld, context dropped 18,282 tokens → 122 tokens and accuracy fell 66.7 → 57.1 — worse than the no-adaptation baseline of 63.7.

**ACE's solution — grow-and-refine:**
Contexts are append-only evolving playbooks. Knowledge accumulates in structured bullet entries; nothing is ever rewritten or erased wholesale.

**Three-Role Architecture:**
- **Generator** — reads the current playbook + question + schema → produces output + reasoning trajectory, referencing which playbook bullets it used
- **Reflector** — *separate from curation* — evaluates generator output against ground truth or user feedback, identifies errors, extracts reusable insights. Keeping reflection separate from curation is key: it improves context quality by preventing the curator from seeing noisy raw outputs
- **Curator** — converts reflector insights into structured delta updates with `helpful/harmful` counters. Uses deterministic merging with de-duplication and pruning. Only ADD/UPDATE/REMOVE operations on individual bullets — never full rewrites

**Results:** +10.6% on AppWorld agent benchmark, +8.6% on financial domain vs strong baselines. Matches GPT-4.1-powered production agents using DeepSeek-V3.1 (smaller open-source model).

---

### 2. BIRD Benchmark (arXiv: 2305.03111)
**Li et al. — Can LLM Already Serve as A Database Interface?**

- **Scale**: 12,751 question-SQL pairs, 95 databases, 33.4 GB total
- **Domains**: 37+ professional domains — blockchain, hockey, healthcare, education, finance
- **Why BIRD is harder than Spider/WikiSQL**:
  - *Dirty database contents*: real-world inconsistent values, nulls, formatting quirks
  - *External knowledge requirement*: questions need domain context not in the schema — the `evidence` field
  - *Schema complexity*: dozens of columns, ambiguous names, non-standard conventions
- **Primary metric**: Execution Accuracy (EX) — does the query's output match gold SQL output? Not string matching.
- **Difficulty levels**: `simple` / `moderate` / `challenging`

**Data format:**
```json
{
  "question_id": 0,
  "db_id": "california_schools",
  "question": "What is the highest eligible free rate for K-12 students in the schools in Alameda County?",
  "evidence": "Eligible free rate for K-12 = `Free Meal Count (K-12)` / `Enrollment (K-12)`",
  "SQL": "SELECT `Free Meal Count (K-12)` / `Enrollment (K-12)` FROM frpm WHERE `County Name` = 'Alameda' ORDER BY (CAST(`Free Meal Count (K-12)` AS REAL) / `Enrollment (K-12)`) DESC LIMIT 1",
  "difficulty": "simple"
}
```

The `evidence` field is the bridge between natural language and database — exactly what the ACE playbook learns to accumulate automatically across interactions.

---

## Project Core Thesis

> Standard text-to-SQL systems treat each question in isolation. ACE allows the agent to accumulate schema-specific heuristics, user intent patterns, and domain knowledge across interactions — improving EX accuracy on BIRD without any model retraining or weight updates.

**What the playbook actually stores** — not generic SQL rules (those converge in ~10 iterations), but:
1. Schema-specific facts: column aliases, naming quirks, non-obvious joins for *this* database
2. User intent patterns: what "recent", "active", "top" means in this specific domain
3. Failure signatures: which query patterns consistently break on this schema
4. Domain knowledge: the same type of facts as BIRD's `evidence` field — learned automatically

---

## Model & Runtime

### Ollama + qwen2.5-coder

All three ACE roles run locally via Ollama. One shared wrapper for all agents:

```python
from ollama import chat

def call_llm(system_prompt: str, user_content: str, expect_json: bool = True) -> str:
    response = chat(
        model='qwen2.5-coder',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_content}
        ],
        format='json' if expect_json else None
    )
    return response.message.content
```

No API keys. No cost. Fully local. qwen2.5-coder is chosen because it has strong SQL and code reasoning capabilities out of the box, which makes it well-suited for both the Generator (SQL) and Reflector/Curator (structured JSON reasoning) roles.

---

## Official ACE Playbook Format

Following the official ACE implementation (`ace-agent/ace` on GitHub), each playbook entry is a bullet with `helpful/harmful` counters:

```
## STRATEGIES & INSIGHTS

[str-00001] helpful=5 harmful=0 :: Always check exact column names via PRAGMA before writing JOINs — this schema uses 'cust_id' not 'customer_id'

[str-00002] helpful=3 harmful=1 :: When question mentions 'recent', default to last 7 days unless evidence field specifies otherwise

## FORMULAS AND CALCULATIONS

[calc-00001] helpful=6 harmful=0 :: Eligible free rate = Free Meal Count (K-12) / Enrollment (K-12) — always CAST numerator as REAL before division to avoid integer truncation

## COMMON MISTAKES TO AVOID

[err-00001] helpful=4 harmful=0 :: Avoid SELECT * on large tables — always specify columns explicitly

[err-00002] helpful=2 harmful=0 :: Do not assume NULL means zero — use COALESCE or IS NOT NULL filters explicitly
```

**Section slugs** (from official `ace/utils.py`):

| Slug | Section |
|------|---------|
| `str` | strategies_and_insights |
| `calc` | formulas_and_calculations |
| `code` | code_snippets_and_templates |
| `err` | common_mistakes_to_avoid |
| `prob` | problem_solving_heuristics |
| `ctx` | context_clues_and_indicators |
| `misc` | others |

**Counter logic:**
- `helpful` increments when a bullet contributes to a correct query (tracked via `bullet_ids` in Generator output)
- `harmful` increments when a bullet was cited but the query still failed
- Curator prunes bullets when `harmful > 3` and `helpful == 0`

---

## The Three Prompt Templates

### Generator Prompt (src/generator.py)

```python
GENERATOR_SYSTEM_PROMPT = """You are a SQLite expert generating SQL queries for the BIRD benchmark.

You have access to a strategy playbook built from past interactions on this database.
Apply the playbook strategies to improve your SQL generation.

PLAYBOOK:
{playbook}

DATABASE SCHEMA:
{schema}

RULES:
- Only use tables and columns that exist in the schema above
- Use SQLite syntax only
- Apply CAST(col AS REAL) before any division
- Check column names exactly — do not assume standard naming
- Use the evidence field when provided — it defines domain-specific formulas
"""

GENERATOR_USER_TEMPLATE = """EXTERNAL KNOWLEDGE / EVIDENCE:
{evidence}

QUESTION: {question}

Think step by step. Reference specific playbook bullet IDs if they apply.
Return JSON only:
{{
  "reasoning": "step by step thinking, referencing playbook entries by ID",
  "bullet_ids": ["str-00001"],
  "final_answer": "SELECT ..."
}}"""
```

### Reflector Prompt (src/reflector.py)

```python
REFLECTOR_SYSTEM_PROMPT = """You are evaluating a text-to-SQL agent's output.
Your job is to identify what went wrong (or right) and extract one reusable insight.
Be specific to this database schema — not generic SQL advice."""

REFLECTOR_USER_TEMPLATE = """QUESTION: {question}
EVIDENCE: {evidence}
GENERATED SQL: {generated_sql}
EXECUTION OUTPUT: {execution_output}
EXPECTED OUTPUT: {expected_output}
USER FEEDBACK: {user_feedback}
PLAYBOOK BULLETS USED: {bullet_ids}

Return JSON only:
{{
  "reasoning": "analysis of what happened",
  "error_identification": "specific error or 'none'",
  "root_cause_analysis": "why did it fail",
  "correct_approach": "what the correct strategy should be",
  "key_insight": "one concise reusable lesson (empty string if no insight worth adding)",
  "bullet_tags": ["str"],
  "outcome": "correct | incorrect | partial"
}}"""
```

### Curator Prompt (src/curator.py)

```python
CURATOR_SYSTEM_PROMPT = """You are the curator of a text-to-SQL agent's strategy playbook.
Convert reflector insights into structured delta updates.

STRICT RULES:
1. NEVER rewrite or delete existing bullet content — only counters may be updated
2. Only ADD a bullet if the insight is genuinely new and reusable across queries
3. UPDATE an existing bullet's helpful/harmful counter if the insight confirms or contradicts it
4. REMOVE only if harmful > 3 and helpful == 0
5. Generic insights like 'check column names' are NOT acceptable — must be schema-specific
6. If no meaningful update is warranted, output NO_OPERATIONS"""

CURATOR_USER_TEMPLATE = """CURRENT PLAYBOOK:
{playbook}

REFLECTOR OUTPUT:
{reflector_output}

Return JSON only:
{{
  "reasoning": "why you chose these operations",
  "operations": [
    {{
      "type": "ADD",
      "section": "str",
      "content": "specific reusable heuristic for this schema",
      "metadata": {{"helpful": 1, "harmful": 0}}
    }},
    {{
      "type": "UPDATE",
      "bullet_id": "str-00001",
      "metadata": {{"helpful_delta": 1, "harmful_delta": 0}}
    }},
    {{
      "type": "REMOVE",
      "bullet_id": "err-00002"
    }}
  ]
}}

Output the string NO_OPERATIONS if no changes are needed."""
```

---

## Feedback Signal Design

**Explicit feedback** (user-provided, collected after every query):
- "Was this the output you expected?" → y/n
- If no: "What did you expect?" (free text passed to Reflector as `expected_output`)
- "Any issue with the SQL itself?" (optional, for SQL-literate users)

**Implicit feedback** (automatic — no user input required):
- SQL syntax error → `failure_type = sql_error`, Reflector runs automatically
- Query returns 0 rows when question implies non-empty result → `failure_type = empty_result`
- Result set columns don't match question's intent → `failure_type = wrong_columns`

Both signals go to the Reflector. The Reflector also runs on *successful* queries to increment `helpful` counters on bullets that were cited and contributed to a correct answer.

---

## Evaluation Strategy

| Metric | Description |
|---|---|
| Execution Accuracy (EX) | % of queries matching gold output — primary BIRD metric |
| EX by difficulty | simple / moderate / challenging breakdown |
| EX over iterations | rounds 1, 5, 10, 20, 50 — the improvement curve |
| Playbook growth | Entry count and total token size over iterations — proves accumulation without collapse |
| Helpful/harmful ratios | Are bullets trending useful or degrading? |
| Bullet citation rate | How often does the Generator reference the playbook? |
| ACE vs static baseline | Same model, same questions, empty playbook — the control condition |

---

## Tech Stack

| Component | Tool |
|---|---|
| Generator / Reflector / Curator | `qwen2.5-coder` via `ollama` Python package |
| Database execution | SQLite via Python `sqlite3` stdlib |
| Playbook storage | Plain `.txt` file per database (`playbooks/{db_id}_playbook.txt`) |
| Interaction logging | `.jsonl` — one JSON object per interaction |
| Evaluation | BIRD official `evaluation.py` (EX metric) |
| UI | Streamlit |
| Dataset | BIRD dev set, 12,751 pairs, 95 SQLite databases |

---

## Papers to Cite

1. Zhang et al. (2026). *Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models.* ICLR 2026. arXiv:2510.04618
2. Li et al. (2023). *Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs.* arXiv:2305.03111
