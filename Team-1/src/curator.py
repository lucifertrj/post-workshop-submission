import json
from src.llm import call_llm
from src.playbook import read_playbook, apply_operations

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

CITED BULLET IDS: {bullet_ids}
OUTCOME: {outcome}

REFLECTOR OUTPUT:
{reflector_output}

Return JSON only, or the string NO_OPERATIONS (only if permitted):
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
      "metadata": {{"helpful_delta": 0, "harmful_delta": 1}}
    }},
    {{
      "type": "REMOVE",
      "bullet_id": "err-00002"
    }}
  ]
}}

MANDATORY RULES:
Rule one: if outcome is correct and bullet_ids is non-empty, issue an UPDATE operation with helpful_delta of 1 for every bullet ID in the list. This must always happen regardless of whether a new insight exists.
Rule two: if outcome is incorrect and bullet_ids is non-empty, issue an UPDATE operation with harmful_delta of 1 for every bullet ID in the list. This must always happen. Then additionally decide whether to ADD a new bullet based on the key insight from the Reflector."""

def curate(db_id: str, reflector_output: dict, bullet_ids: list, outcome: str) -> list:
    # Only run curator if there is a key insight, UNLESS there are bullet_ids to update
    if not reflector_output.get("key_insight") and reflector_output.get("outcome") == "correct" and not bullet_ids:
        return []
    
    playbook = read_playbook(db_id)
    system = CURATOR_SYSTEM_PROMPT
    user = CURATOR_USER_TEMPLATE.format(
        playbook=playbook,
        reflector_output=json.dumps(reflector_output, indent=2),
        bullet_ids=json.dumps(bullet_ids),
        outcome=outcome
    )
    raw = call_llm(system, user, expect_json=False).strip()
    
    print("\n--- [CURATOR] LLM Output ---")
    print(raw)
    print("----------------------------\n")
    
    if raw == "NO_OPERATIONS":
        return []
    
    try:
        # Strip markdown formatting
        if raw.startswith("```json"):
            raw = raw[7:]
        elif raw.startswith("```"):
            raw = raw[3:]
        
        if raw.endswith("```"):
            raw = raw[:-3]
            
        raw = raw.strip()
        
        if not raw.startswith("{"):
            return []
            
        result = json.loads(raw)
        operations = result.get("operations", [])
        apply_operations(db_id, operations)
        return operations
    except json.JSONDecodeError:
        return []
