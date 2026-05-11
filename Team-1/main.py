import os
import jsonlines

from src.generator import generate
from src.executor import execute_sql
from src.reflector import reflect
from src.curator import curate
from src.feedback import collect_interactive_feedback
from src.playbook import get_entry_count, apply_operations
import logging

logging.basicConfig(level=logging.INFO)

def run_interaction(question: str, db_id: str, evidence: str = "") -> dict:
    # Step 1: Generate
    print("\n[Gen] Generating SQL...")
    gen_output = generate(question, db_id, evidence)
    sql = gen_output.get("final_answer", "")
    bullet_ids = gen_output.get("bullet_ids", [])
    print(f"\nGenerated SQL:\n{sql}")
    if bullet_ids:
        print(f"Playbook bullets cited: {bullet_ids}")
    
    # Step 2: Execute
    exec_result = execute_sql(db_id, sql)
    
    # Step 3: Collect feedback
    feedback = collect_interactive_feedback(question, exec_result)
    
    # Step 4 & 5: Reflect and Curate
    if feedback["correct"] and bullet_ids:
        print("\n[Curate] Mechanically updating helpful counters...")
        ops = [{"type": "UPDATE", "bullet_id": bid, "metadata": {"helpful_delta": 1, "harmful_delta": 0}} for bid in bullet_ids]
        apply_operations(db_id, ops)
        reflector_output = {}
        operations = ops
    elif not feedback["correct"]:
        print("\n[Reflect] Reflecting on failed result...")
        exec_output_val = exec_result["error"] if not exec_result["success"] else exec_result["result"]
        reflector_output = reflect(
            question=question,
            evidence=evidence,
            generated_sql=sql,
            execution_output=exec_output_val,
            expected_output=feedback["expected_output"],
            user_feedback=feedback["sql_feedback"],
            bullet_ids=bullet_ids
        )
        
        print("[Curate] Curating playbook updates...")
        operations = curate(db_id, reflector_output, bullet_ids, "incorrect")
    else:
        reflector_output = {}
        operations = []
    
    # Log
    os.makedirs("logs", exist_ok=True)
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
    print("=== ACE Text-to-SQL Agent (Interactive Mode) ===")
    db_id = input("Database (e.g. california_schools): ").strip()
    if not db_id:
        db_id = "california_schools"
    while True:
        question = input("\nQuestion (or 'quit'): ").strip()
        if question == 'quit':
            break
        if not question:
            continue
        evidence = input("Evidence (press enter to skip): ").strip()
        run_interaction(question, db_id, evidence)
