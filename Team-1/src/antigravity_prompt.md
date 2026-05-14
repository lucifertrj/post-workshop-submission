# Antigravity Prompt — ACE Text-to-SQL Agent

Paste this entire prompt into Cursor, Windsurf, or any AI coding assistant to bootstrap the project.

---

## Prompt

You are helping me build a research project: **Self-Improving Text-to-SQL Agent via Agentic Context Engineering (ACE)**.

---

### What we are building

A text-to-SQL agent that improves query accuracy over time using the ACE framework (arXiv:2510.04618). The agent has three roles — Generator, Reflector, Curator — that work together to maintain an evolving strategy playbook. No model fine-tuning. No API keys. Everything runs locally via Ollama.

**Full loop:**
1. User asks a natural language question about a database
2. **Generator** reads current playbook + schema + question → generates SQL + reasoning + which playbook bullets it used
3. SQL executes against SQLite → result shown to user
4. User provides feedback (or ground truth is used in batch mode)
5. **Reflector** evaluates the output → extracts a reusable insight
6. **Curator** converts insight into ADD/UPDATE/REMOVE operations on the playbook
7. Next query uses the updated playbook → measurably better over time

---

### Model

All three roles use `qwen2.5-coder` via Ollama:

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

---

### Dataset

**BIRD Benchmark** (arXiv:2305.03111). Each sample:
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

Databases are SQLite `.sqlite` files. Use Python `sqlite3` stdlib — no external DB library needed.

---

### Project structure

```
ace-text2sql/
├── data/
│   ├── bird/                        # BIRD dev.json
│   └── databases/                   # .sqlite files
├── playbooks/
│   └── {db_id}_playbook.txt         # One per database, starts empty
├── logs/
│   └── interactions.jsonl
├── results/
│   └── experiment_TIMESTAMP.csv
├── src/
│   ├── llm.py                       # call_llm wrapper
│   ├── executor.py                  # SQLite execution
│   ├── playbook.py                  # Read/write/apply operations
│   ├── generator.py                 # Generator agent + prompt
│   ├── reflector.py                 # Reflector agent + prompt
│   ├── curator.py                   # Curator agent + prompt
│   └── feedback.py                  # Explicit + implicit feedback
├── main.py                          # Interactive CLI loop
├── run_experiment.py                # Batch controlled evaluation
├── app.py                           # Streamlit UI
└── requirements.txt
```

---

### Playbook format

Follow the official ACE playbook format exactly:

```
## STRATEGIES & INSIGHTS

[str-00001] helpful=5 harmful=0 :: Always verify column names via PRAGMA — this schema uses 'cust_id' not 'customer_id'

[str-00002] helpful=3 harmful=1 :: When question says 'recent', default to last 7 days unless evidence specifies otherwise

## FORMULAS AND CALCULATIONS

[calc-00001] helpful=6 harmful=0 :: Eligible free rate = Free Meal Count (K-12) / Enrollment (K-12) — always CAST numerator as REAL before division

## COMMON MISTAKES TO AVOID

[err-00001] helpful=4 harmful=0 :: Avoid SELECT * on large tables — specify columns explicitly
```

Section slugs: `str` (strategies), `calc` (formulas), `code` (templates), `err` (mistakes), `prob` (heuristics), `ctx` (context clues), `misc` (other)

Counter rule: `helpful` up when bullet was cited and query succeeded. `harmful` up when bullet was cited but query still failed. Prune if `harmful > 3` and `helpful == 0`.

---

### File-by-file specifications

#### `src/llm.py`
```python
from ollama import chat
import json

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

def call_llm_json(system_prompt: str, user_content: str) -> dict:
    raw = call_llm(system_prompt, user_content, expect_json=True)
    # Strip markdown code fences if model adds them
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)
```

#### `src/executor.py`
```python
import sqlite3, os

def get_schema(db_id: str, db_dir: str = "data/databases") -> str:
    """Return CREATE TABLE statements for all tables in the database."""
    db_path = os.path.join(db_dir, db_id, f"{db_id}.sqlite")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    schema_parts = []
    for table in tables:
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE name='{table}'")
        ddl = cursor.fetchone()
        if ddl:
            schema_parts.append(ddl[0])
    conn.close()
    return "\n\n".join(schema_parts)

def execute_sql(db_id: str, sql: str, db_dir: str = "data/databases", timeout: int = 5) -> dict:
    db_path = os.path.join(db_dir, db_id, f"{db_id}.sqlite")
    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        cursor = conn.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        return {
            "success": True,
            "result": result,
            "columns": columns,
            "rows_returned": len(result),
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "result": [],
            "columns": [],
            "rows_returned": 0,
            "error": str(e)
        }
```

#### `src/playbook.py`
```python
import os, re
from datetime import date

PLAYBOOK_DIR = "playbooks"
SECTION_ORDER = [
    "STRATEGIES & INSIGHTS",
    "FORMULAS AND CALCULATIONS",
    "CODE SNIPPETS AND TEMPLATES",
    "COMMON MISTAKES TO AVOID",
    "PROBLEM SOLVING HEURISTICS",
    "CONTEXT CLUES AND INDICATORS",
    "OTHERS"
]
SLUG_TO_SECTION = {
    "str": "STRATEGIES & INSIGHTS",
    "calc": "FORMULAS AND CALCULATIONS",
    "code": "CODE SNIPPETS AND TEMPLATES",
    "err": "COMMON MISTAKES TO AVOID",
    "prob": "PROBLEM SOLVING HEURISTICS",
    "ctx": "CONTEXT CLUES AND INDICATORS",
    "misc": "OTHERS"
}

def _playbook_path(db_id: str) -> str:
    os.makedirs(PLAYBOOK_DIR, exist_ok=True)
    return os.path.join(PLAYBOOK_DIR, f"{db_id}_playbook.txt")

def read_playbook(db_id: str) -> str:
    path = _playbook_path(db_id)
    if not os.path.exists(path):
        return "## STRATEGIES & INSIGHTS\n\n(no entries yet)\n"
    return open(path).read()

def get_entry_count(db_id: str) -> int:
    content = read_playbook(db_id)
    return len(re.findall(r'\[(?:str|calc|code|err|prob|ctx|misc)-\d{5}\]', content))

def reset_playbook(db_id: str):
    path = _playbook_path(db_id)
    if os.path.exists(path):
        os.remove(path)

def apply_operations(db_id: str, operations: list):
    """Apply ADD/UPDATE/REMOVE operations to the playbook."""
    content = read_playbook(db_id)
    
    for op in operations:
        op_type = op.get("type")
        
        if op_type == "ADD":
            slug = op.get("section", "str")
            section = SLUG_TO_SECTION.get(slug, "STRATEGIES & INSIGHTS")
            # Find next bullet ID for this slug
            existing = re.findall(rf'\[{slug}-(\d{{5}})\]', content)
            next_num = max([int(n) for n in existing], default=0) + 1
            bullet_id = f"[{slug}-{next_num:05d}]"
            helpful = op.get("metadata", {}).get("helpful", 1)
            harmful = op.get("metadata", {}).get("harmful", 0)
            entry = f"\n{bullet_id} helpful={helpful} harmful={harmful} :: {op['content']}\n"
            # Append to correct section or create section
            if f"## {section}" in content:
                content = content.replace(f"## {section}", f"## {section}{entry}", 1)
            else:
                content += f"\n## {section}{entry}"
        
        elif op_type == "UPDATE":
            bullet_id = op.get("bullet_id")
            if bullet_id:
                helpful_delta = op.get("metadata", {}).get("helpful_delta", 0)
                harmful_delta = op.get("metadata", {}).get("harmful_delta", 0)
                def update_counters(match):
                    h = int(match.group(1)) + helpful_delta
                    d = int(match.group(2)) + harmful_delta
                    return f"helpful={h} harmful={d}"
                escaped = re.escape(bullet_id)
                content = re.sub(
                    rf'({escaped} )helpful=(\d+) harmful=(\d+)',
                    lambda m: m.group(1) + f"helpful={int(m.group(2))+helpful_delta} harmful={int(m.group(3))+harmful_delta}",
                    content
                )
        
        elif op_type == "REMOVE":
            bullet_id = op.get("bullet_id")
            if bullet_id:
                escaped = re.escape(bullet_id)
                content = re.sub(rf'\n{escaped}[^\n]+\n', '\n', content)
    
    with open(_playbook_path(db_id), 'w') as f:
        f.write(content)
```

#### `src/generator.py`
```python
from .llm import call_llm_json
from .playbook import read_playbook
from .executor import get_schema

GENERATOR_SYSTEM_PROMPT = """You are a SQLite expert generating SQL queries for the BIRD benchmark.

You have a strategy playbook built from past interactions on this database.
Apply the playbook strategies to improve your SQL generation.

PLAYBOOK:
{playbook}

DATABASE SCHEMA:
{schema}

RULES:
- Only use tables and columns that exist in the schema above
- Use SQLite syntax only (no LIMIT without ORDER BY, no window functions unless needed)
- Apply CAST(col AS REAL) before any division to avoid integer truncation
- Check column names exactly — do not assume standard naming conventions
- Use the evidence field when provided — it defines domain-specific formulas and definitions
- Reference playbook bullet IDs in your reasoning if they apply"""

GENERATOR_USER_TEMPLATE = """EXTERNAL KNOWLEDGE / EVIDENCE:
{evidence}

QUESTION: {question}

Think step by step. Reference specific playbook bullet IDs in your reasoning if they apply.
Return JSON only — no text outside the JSON object:
{{
  "reasoning": "step by step thinking, citing playbook entries by ID where applicable",
  "bullet_ids": ["str-00001", "calc-00001"],
  "final_answer": "SELECT ..."
}}"""

def generate(question: str, db_id: str, evidence: str = "") -> dict:
    playbook = read_playbook(db_id)
    schema = get_schema(db_id)
    system = GENERATOR_SYSTEM_PROMPT.format(playbook=playbook, schema=schema)
    user = GENERATOR_USER_TEMPLATE.format(evidence=evidence or "None provided", question=question)
    result = call_llm_json(system, user)
    return result  # {reasoning, bullet_ids, final_answer}
```

#### `src/reflector.py`
```python
from .llm import call_llm_json

REFLECTOR_SYSTEM_PROMPT = """You are evaluating a text-to-SQL agent's output for the BIRD benchmark.
Your job is to identify what went wrong (or right) and extract one reusable schema-specific insight.

Be specific to this database — generic SQL advice like 'check column names' is not useful.
Good insight example: 'In california_schools, county is stored as County Name with space, not county_name'"""

REFLECTOR_USER_TEMPLATE = """QUESTION: {question}
EVIDENCE: {evidence}
GENERATED SQL: {generated_sql}
EXECUTION OUTPUT: {execution_output}
EXPECTED OUTPUT: {expected_output}
USER FEEDBACK: {user_feedback}
PLAYBOOK BULLETS CITED BY GENERATOR: {bullet_ids}

Return JSON only:
{{
  "reasoning": "detailed analysis of what happened",
  "error_identification": "specific error description or 'none'",
  "root_cause_analysis": "why did it fail, or why it succeeded",
  "correct_approach": "what the correct strategy is",
  "key_insight": "one concise reusable lesson specific to this schema (empty string if nothing new)",
  "bullet_tags": ["str"],
  "outcome": "correct | incorrect | partial"
}}"""

def reflect(question: str, evidence: str, generated_sql: str, execution_output: str,
            expected_output: str, user_feedback: str, bullet_ids: list) -> dict:
    system = REFLECTOR_SYSTEM_PROMPT
    user = REFLECTOR_USER_TEMPLATE.format(
        question=question,
        evidence=evidence or "None",
        generated_sql=generated_sql,
        execution_output=str(execution_output)[:500],  # truncate long results
        expected_output=str(expected_output)[:500],
        user_feedback=user_feedback or "None",
        bullet_ids=str(bullet_ids)
    )
    return call_llm_json(system, user)
```

#### `src/curator.py`
```python
import json
from .llm import call_llm
from .playbook import read_playbook, apply_operations

CURATOR_SYSTEM_PROMPT = """You are the curator of a text-to-SQL agent's strategy playbook.
Convert reflector insights into structured delta updates using ADD, UPDATE, or REMOVE operations.

STRICT RULES — follow exactly:
1. NEVER rewrite or delete existing bullet content — only counters may be updated via UPDATE
2. Only ADD a bullet if the insight is genuinely new and reusable across multiple queries
3. UPDATE an existing bullet's helpful/harmful counter if this interaction confirms or contradicts it
4. REMOVE only when harmful > 3 AND helpful == 0
5. Insights like 'check column names' are NOT specific enough — must reference schema details
6. If outcome was 'correct', only UPDATE helpful counters — do not ADD unless truly novel
7. If no meaningful change is warranted, output exactly: NO_OPERATIONS"""

CURATOR_USER_TEMPLATE = """CURRENT PLAYBOOK:
{playbook}

REFLECTOR OUTPUT:
{reflector_output}

Return JSON only, or the string NO_OPERATIONS:
{{
  "reasoning": "why you chose these operations",
  "operations": [
    {{
      "type": "ADD",
      "section": "str",
      "content": "specific reusable heuristic referencing this schema",
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
}}"""

def curate(db_id: str, reflector_output: dict) -> list:
    # Only run curator if there is a key insight
    if not reflector_output.get("key_insight") and reflector_output.get("outcome") == "correct":
        # On correct with no insight: just increment helpful counters for cited bullets
        # (handled externally via UPDATE operations)
        return []
    
    playbook = read_playbook(db_id)
    system = CURATOR_SYSTEM_PROMPT
    user = CURATOR_USER_TEMPLATE.format(
        playbook=playbook,
        reflector_output=json.dumps(reflector_output, indent=2)
    )
    raw = call_llm(system, user, expect_json=False).strip()
    
    if raw == "NO_OPERATIONS" or not raw.startswith("{"):
        return []
    
    try:
        result = json.loads(raw)
        operations = result.get("operations", [])
        apply_operations(db_id, operations)
        return operations
    except json.JSONDecodeError:
        return []
```

#### `src/feedback.py`
```python
def collect_interactive_feedback(question: str, execution_result: dict) -> dict:
    """Interactive mode: ask the user."""
    if not execution_result["success"]:
        print(f"SQL Error: {execution_result['error']}")
        return {
            "correct": False,
            "expected_output": "query failed with error",
            "sql_feedback": execution_result["error"],
            "failure_type": "sql_error"
        }
    
    print(f"\nResult ({execution_result['rows_returned']} rows):")
    for row in execution_result["result"][:5]:
        print(" ", row)
    if execution_result["rows_returned"] > 5:
        print(f"  ... and {execution_result['rows_returned'] - 5} more rows")
    
    # Implicit: empty result on question expecting data
    question_lower = question.lower()
    if execution_result["rows_returned"] == 0 and any(
        question_lower.startswith(w) for w in ["what", "which", "find", "list", "show", "how many"]
    ):
        print("Note: Query returned 0 rows. This may be unexpected.")
    
    correct = input("\nWas this correct? (y/n): ").strip().lower() == 'y'
    expected = ""
    sql_feedback = ""
    if not correct:
        expected = input("What did you expect? ").strip()
        sql_feedback = input("Any issue with the SQL? (press enter to skip): ").strip()
    
    return {
        "correct": correct,
        "expected_output": expected,
        "sql_feedback": sql_feedback,
        "failure_type": "user_rejected" if not correct else "none"
    }

def collect_batch_feedback(execution_result: dict, gold_result: list) -> dict:
    """Batch mode: compare against BIRD gold SQL output automatically."""
    if not execution_result["success"]:
        return {
            "correct": False,
            "expected_output": str(gold_result),
            "sql_feedback": execution_result["error"],
            "failure_type": "sql_error"
        }
    
    # Sort both for set comparison (BIRD EX metric)
    gen = sorted([str(r) for r in execution_result["result"]])
    gold = sorted([str(r) for r in gold_result])
    correct = gen == gold
    
    return {
        "correct": correct,
        "expected_output": str(gold_result) if not correct else "",
        "sql_feedback": "",
        "failure_type": "wrong_result" if not correct else "none"
    }
```

#### `main.py` — Interactive CLI loop
```python
import json
from src.generator import generate
from src.executor import execute_sql
from src.reflector import reflect
from src.curator import curate
from src.feedback import collect_interactive_feedback
from src.playbook import get_entry_count
import logging, jsonlines

logging.basicConfig(level=logging.INFO)

def run_interaction(question: str, db_id: str, evidence: str = "") -> dict:
    # Step 1: Generate
    gen_output = generate(question, db_id, evidence)
    sql = gen_output.get("final_answer", "")
    bullet_ids = gen_output.get("bullet_ids", [])
    print(f"\nGenerated SQL:\n{sql}")
    
    # Step 2: Execute
    exec_result = execute_sql(db_id, sql)
    
    # Step 3: Collect feedback
    feedback = collect_interactive_feedback(question, exec_result)
    
    # Step 4: Reflect
    reflector_output = reflect(
        question=question,
        evidence=evidence,
        generated_sql=sql,
        execution_output=exec_result["result"],
        expected_output=feedback["expected_output"],
        user_feedback=feedback["sql_feedback"],
        bullet_ids=bullet_ids
    )
    
    # Step 5: Curate
    operations = curate(db_id, reflector_output)
    
    # Log
    interaction = {
        "question": question, "db_id": db_id, "sql": sql,
        "correct": feedback["correct"], "bullet_ids": bullet_ids,
        "reflector": reflector_output, "operations": operations,
        "playbook_size": get_entry_count(db_id)
    }
    with jsonlines.open("logs/interactions.jsonl", mode='a') as writer:
        writer.write(interaction)
    
    print(f"Playbook entries: {get_entry_count(db_id)}")
    return interaction

if __name__ == "__main__":
    db_id = input("Database (e.g. california_schools): ").strip()
    while True:
        question = input("\nQuestion (or 'quit'): ").strip()
        if question == 'quit':
            break
        evidence = input("Evidence (press enter to skip): ").strip()
        run_interaction(question, db_id, evidence)
```

#### `run_experiment.py` — Batch controlled evaluation
```python
import json, csv, os
from datetime import datetime
from src.generator import generate
from src.executor import execute_sql
from src.reflector import reflect
from src.curator import curate
from src.feedback import collect_batch_feedback
from src.playbook import get_entry_count, reset_playbook

def run_gold_sql(db_id: str, gold_sql: str) -> list:
    result = execute_sql(db_id, gold_sql)
    return result["result"] if result["success"] else []

def run_experiment(db_id: str, samples: list, playbook_enabled: bool = True,
                   eval_every: int = 5) -> list:
    if not playbook_enabled:
        reset_playbook(db_id)
    
    records = []
    correct_count = 0
    
    for i, sample in enumerate(samples):
        question = sample["question"]
        evidence = sample.get("evidence", "")
        gold_sql = sample["SQL"]
        difficulty = sample["difficulty"]
        
        # Generate
        gen_output = generate(question, db_id, evidence)
        sql = gen_output.get("final_answer", "")
        bullet_ids = gen_output.get("bullet_ids", [])
        
        # Execute
        exec_result = execute_sql(db_id, sql)
        gold_result = run_gold_sql(db_id, gold_sql)
        
        # Batch feedback
        feedback = collect_batch_feedback(exec_result, gold_result)
        if feedback["correct"]:
            correct_count += 1
        
        # ACE loop (only if enabled)
        if playbook_enabled:
            ref_output = reflect(
                question=question, evidence=evidence, generated_sql=sql,
                execution_output=exec_result["result"],
                expected_output=feedback["expected_output"],
                user_feedback="", bullet_ids=bullet_ids
            )
            curate(db_id, ref_output)
        
        # Record metrics every eval_every steps
        if (i + 1) % eval_every == 0:
            records.append({
                "iteration": i + 1,
                "ex_accuracy": correct_count / (i + 1),
                "playbook_entries": get_entry_count(db_id),
                "playbook_enabled": playbook_enabled
            })
            print(f"[{i+1}/{len(samples)}] EX: {correct_count/(i+1):.3f} | Playbook: {get_entry_count(db_id)} entries")
    
    return records

if __name__ == "__main__":
    import json
    with open("data/bird/dev.json") as f:
        all_samples = json.load(f)
    
    # Filter to chosen database
    db_id = "california_schools"
    samples = [s for s in all_samples if s["db_id"] == db_id][:100]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Run baseline (no playbook)
    print("=== BASELINE (no playbook) ===")
    reset_playbook(db_id)
    baseline_records = run_experiment(db_id, samples, playbook_enabled=False)
    
    # Run ACE
    print("=== ACE (with playbook) ===")
    reset_playbook(db_id)
    ace_records = run_experiment(db_id, samples, playbook_enabled=True)
    
    # Save results
    os.makedirs("results", exist_ok=True)
    with open(f"results/experiment_{timestamp}.csv", "w") as f:
        writer = csv.DictWriter(f, fieldnames=["iteration", "ex_accuracy", "playbook_entries", "playbook_enabled"])
        writer.writeheader()
        writer.writerows(baseline_records + ace_records)
    print(f"Saved to results/experiment_{timestamp}.csv")
```

#### `app.py` — Streamlit UI
```python
import streamlit as st
import json
from src.generator import generate
from src.executor import execute_sql, get_schema
from src.reflector import reflect
from src.curator import curate
from src.feedback import collect_batch_feedback
from src.playbook import read_playbook, reset_playbook, get_entry_count
import pandas as pd

st.set_page_config(layout="wide", page_title="ACE Text-to-SQL")

col_chat, col_playbook = st.columns([1.2, 1])

with col_playbook:
    st.subheader("Live Playbook")
    db_id = st.selectbox("Database", ["california_schools", "financial", "hockey"])
    entry_count = get_entry_count(db_id)
    st.caption(f"{entry_count} entries")
    playbook_display = st.empty()
    playbook_display.code(read_playbook(db_id), language="markdown")
    if st.button("Reset Playbook"):
        reset_playbook(db_id)
        st.rerun()

with col_chat:
    st.subheader("Text-to-SQL Agent")
    playbook_on = st.toggle("ACE Playbook Enabled", value=True)
    question = st.text_input("Ask a question about the database")
    evidence = st.text_input("Evidence / External Knowledge (optional)")
    
    if st.button("Run Query") and question:
        with st.spinner("Generating SQL..."):
            gen_output = generate(question, db_id, evidence)
            sql = gen_output.get("final_answer", "")
            bullet_ids = gen_output.get("bullet_ids", [])
        
        st.code(sql, language="sql")
        
        with st.spinner("Executing..."):
            exec_result = execute_sql(db_id, sql)
        
        if exec_result["success"]:
            if exec_result["rows_returned"] > 0:
                df = pd.DataFrame(exec_result["result"], columns=exec_result["columns"])
                st.dataframe(df)
            else:
                st.warning("Query returned 0 rows")
        else:
            st.error(f"SQL Error: {exec_result['error']}")
        
        st.caption(f"Playbook bullets cited: {bullet_ids}")
        
        # Feedback
        correct = st.radio("Was this correct?", ["Yes", "No"])
        expected = ""
        if correct == "No":
            expected = st.text_input("What did you expect?")
        
        if st.button("Submit Feedback"):
            if playbook_on:
                with st.spinner("Updating playbook..."):
                    ref_output = reflect(
                        question=question, evidence=evidence, generated_sql=sql,
                        execution_output=exec_result["result"],
                        expected_output=expected, user_feedback="",
                        bullet_ids=bullet_ids
                    )
                    curate(db_id, ref_output)
                    playbook_display.code(read_playbook(db_id), language="markdown")
                    st.success(f"Playbook updated: {get_entry_count(db_id)} entries")
```

---

### requirements.txt

```
ollama
streamlit
pandas
jsonlines
```

---

### Build order

**Do not start with the UI. Build in this exact order:**

1. `src/llm.py` → test with a single `call_llm_json` call
2. `src/executor.py` → verify 5 manual SQL queries work against a BIRD database
3. `src/playbook.py` → test ADD/UPDATE/REMOVE operations manually
4. `src/generator.py` → basic generation with schema, no playbook yet
5. `src/reflector.py` → test on a known wrong query
6. `src/curator.py` → verify it produces valid operations and applies them
7. `main.py` → wire the full CLI loop, test 20 interactions manually
8. `run_experiment.py` → batch evaluation, produce your result CSV
9. `app.py` → Streamlit UI last

---

### Critical constraints

1. Curator must NEVER rewrite existing bullet content — only counters change via UPDATE
2. Generator must read the FULL playbook on every query — do not summarise or truncate it
3. Every interaction gets logged to `interactions.jsonl` regardless of success or failure
4. One playbook file per database — never mix heuristics across databases
5. Baseline condition uses `reset_playbook(db_id)` before running — same code, playbook wiped
6. `format='json'` in the Ollama call enforces JSON output from qwen2.5-coder — always use it for Reflector and Curator calls
