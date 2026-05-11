from src.llm import call_llm_json

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
  "outcome": "correct | incorrect | partial",
  "bullet_ids": {bullet_ids}
}}"""

def reflect(question: str, evidence: str, generated_sql: str, execution_output: str,
            expected_output: str, user_feedback: str, bullet_ids: list) -> dict:
    import json
    system = REFLECTOR_SYSTEM_PROMPT
    user = REFLECTOR_USER_TEMPLATE.format(
        question=question,
        evidence=evidence or "None",
        generated_sql=generated_sql,
        execution_output=str(execution_output)[:500],  # truncate long results
        expected_output=str(expected_output)[:500],
        user_feedback=user_feedback or "None",
        bullet_ids=json.dumps(bullet_ids)
    )
    result = call_llm_json(system, user)
    result["bullet_ids"] = bullet_ids
    print("\n--- [REFLECTOR] LLM Output ---")
    print(json.dumps(result, indent=2))
    print("------------------------------\n")
    return result
