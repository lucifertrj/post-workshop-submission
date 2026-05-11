from src.llm import call_llm_json
from src.playbook import read_playbook
from src.executor import get_schema

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
If no playbook bullet points apply, return an empty list [] for "bullet_ids". Do not return the default example IDs.
Return JSON only — no text outside the JSON object:
{{
  "reasoning": "step by step thinking, citing playbook entries by ID where applicable",
  "bullet_ids": Example : ["str-00001", "calc-00001"] (Do not return the default example IDs),
  "final_answer": "SELECT ..."
}}"""

def generate(question: str, db_id: str, evidence: str = "") -> dict:
    playbook = read_playbook(db_id)
    schema = get_schema(db_id)
    system = GENERATOR_SYSTEM_PROMPT.format(playbook=playbook, schema=schema)
    user = GENERATOR_USER_TEMPLATE.format(evidence=evidence or "None provided", question=question)
    result = call_llm_json(system, user)
    import json
    print("\n--- [GENERATOR] LLM Output ---")
    print(json.dumps(result, indent=2))
    print("------------------------------\n")
    return result
