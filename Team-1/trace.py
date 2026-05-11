import json
from src.reflector import reflect
from src.curator import curate
from src.playbook import read_playbook, reset_playbook, get_entry_count

db_id = "test_db"
reset_playbook(db_id)

# Create the initial playbook with one bullet
with open(f"playbooks/{db_id}_playbook.txt", "w", encoding="utf-8") as f:
    f.write("## STRATEGIES & INSIGHTS\n\n[str-00001] helpful=0 harmful=0 :: Test baseline bullet\n")

bullet_ids = ["[str-00001]"]
question = "How many K-12 students are there in Alameda County?"
evidence = ""
generated_sql = "SELECT Count FROM students;"
exec_output_val = "no such table: students"
expected_output = "SELECT SUM(Enrollment) FROM frpm WHERE County = 'Alameda';"

print("--- Initial playbook ---")
print(read_playbook(db_id))

print("\n--- Running Reflector ---")
ref_output = reflect(
    question=question,
    evidence=evidence,
    generated_sql=generated_sql,
    execution_output=exec_output_val,
    expected_output=expected_output,
    user_feedback="",
    bullet_ids=bullet_ids
)
print("Reflector output dictionary:")
print(json.dumps(ref_output, indent=2))

print("\n--- Running Curator ---")
outcome_str = "incorrect"
ops = curate(db_id, ref_output, bullet_ids, outcome_str)

print("\n--- Final playbook ---")
print(read_playbook(db_id))


