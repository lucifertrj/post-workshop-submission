import os
import re

PLAYBOOK_DIR = "playbooks"
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
    """Read full content of the playbook."""
    path = _playbook_path(db_id)
    if not os.path.exists(path):
        return "## STRATEGIES & INSIGHTS\n\n(no entries yet)"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def get_entry_count(db_id: str) -> int:
    """Count number of entries based on standard bullet tag syntax."""
    content = read_playbook(db_id)
    return len(re.findall(r'\[(?:str|calc|code|err|prob|ctx|misc)-\d{5}\]', content))

def reset_playbook(db_id: str):
    """Empty out a playbook entirely."""
    path = _playbook_path(db_id)
    if os.path.exists(path):
        os.remove(path)

def apply_operations(db_id: str, operations: list):
    """Apply ADD/UPDATE/REMOVE operations."""
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
            entry = f"\n{bullet_id} helpful={helpful} harmful={harmful} :: {op.get('content', '')}\n"
            
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
                
                # We expect the format `[slug-12345] helpful=X harmful=Y ::`
                escaped = re.escape(bullet_id)
                # re.sub needs a function to do dynamic value update
                def update_counters(match):
                    h = int(match.group(2)) + helpful_delta
                    d = int(match.group(3)) + harmful_delta
                    return f"{match.group(1)}helpful={h} harmful={d}"
                
                content = re.sub(
                    rf'({escaped} )helpful=(\d+) harmful=(\d+)',
                    update_counters,
                    content
                )
                
        elif op_type == "REMOVE":
            bullet_id = op.get("bullet_id")
            if bullet_id:
                escaped = re.escape(bullet_id)
                content = re.sub(rf'\n{escaped}[^\n]*\n', '\n', content)

    with open(_playbook_path(db_id), 'w', encoding="utf-8") as f:
        f.write(content.strip() + "\n")
