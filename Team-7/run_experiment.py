import json, csv, os
from datetime import datetime

from src.generator import generate
from src.executor import execute_sql
from src.reflector import reflect
from src.curator import curate
from src.feedback import collect_batch_feedback
from src.playbook import get_entry_count, reset_playbook, apply_operations

def run_gold_sql(db_id: str, gold_sql: str) -> list:
    result = execute_sql(db_id, gold_sql)
    return result["result"] if result["success"] else []

def run_experiment(db_id: str, samples: list, playbook_enabled: bool = True,
                   eval_every: int = 5) -> list:
    """Run batch offline evaluation to compute Execution Accuracy (EX)."""
    # if not playbook_enabled:
    #     reset_playbook(db_id)
    
    records = []
    correct_count = 0
    diff_stats = {
        "simple": {"correct": 0, "total": 0},
        "moderate": {"correct": 0, "total": 0},
        "challenging": {"correct": 0, "total": 0}
    }
    
    for i, sample in enumerate(samples):
        question = sample["question"]
        evidence = sample.get("evidence", "")
        gold_sql = sample["SQL"]
        difficulty = sample.get("difficulty", "simple")
        
        # Step 1: Generate
        gen_output = generate(question, db_id, evidence)
        sql = gen_output.get("final_answer", "")
        bullet_ids = gen_output.get("bullet_ids", [])
        
        # Step 2: Execute
        exec_result = execute_sql(db_id, sql)
        gold_result = run_gold_sql(db_id, gold_sql)
        
        # Update difficulty totals
        diff_stats[difficulty]["total"] += 1
        
        # Step 3: Batch feedback
        feedback = collect_batch_feedback(exec_result, gold_result)
        if feedback["correct"]:
            correct_count += 1
            diff_stats[difficulty]["correct"] += 1
        
        # Step 4 & 5: ACE loop (only if enabled)
        if playbook_enabled:
            if not feedback["correct"]:
                exec_output_val = exec_result["error"] if not exec_result["success"] else exec_result["result"]
                ref_output = reflect(
                    question=question, evidence=evidence, generated_sql=sql,
                    execution_output=exec_output_val,
                    expected_output=feedback["expected_output"],
                    user_feedback="", bullet_ids=bullet_ids
                )
                curate(db_id, ref_output, bullet_ids, "incorrect")
            elif bullet_ids:
                ops = [{"type": "UPDATE", "bullet_id": bid, "metadata": {"helpful_delta": 1, "harmful_delta": 0}} for bid in bullet_ids]
                apply_operations(db_id, ops)
        
        # Record metrics every eval_every steps
        if (i + 1) % eval_every == 0 or (i + 1) == len(samples):
            simple_acc = diff_stats["simple"]["correct"] / diff_stats["simple"]["total"] if diff_stats["simple"]["total"] > 0 else 0.0
            mod_acc = diff_stats["moderate"]["correct"] / diff_stats["moderate"]["total"] if diff_stats["moderate"]["total"] > 0 else 0.0
            chal_acc = diff_stats["challenging"]["correct"] / diff_stats["challenging"]["total"] if diff_stats["challenging"]["total"] > 0 else 0.0
            
            records.append({
                "iteration": i + 1,
                "ex_accuracy": correct_count / (i + 1),
                "simple_acc": simple_acc,
                "moderate_acc": mod_acc,
                "challenging_acc": chal_acc,
                "playbook_entries": get_entry_count(db_id),
                "playbook_enabled": playbook_enabled
            })
            print(f"[{i+1}/{len(samples)}] EX Accuracy: {correct_count/(i+1):.3f} | Playbook Entries: {get_entry_count(db_id)}")
    
    return records

if __name__ == "__main__":
    try:
        with open("data/bird/dev.json", "r", encoding="utf-8") as f:
            all_samples = json.load(f)
    except FileNotFoundError:
        print("BIRD dev set not found at data/bird/dev.json.")
        print("Please download it and place it there before running experiments.")
        exit(1)
    
    # Filter to chosen database configuration
    db_id = "california_schools"
    samples = [s for s in all_samples if s["db_id"] == db_id]
    
    # Run only against first 50 as per roadmap batch suggestions
    samples = samples[:120]
    
    if not samples:
        print(f"No samples found for db_id: {db_id}. Please check dataset.")
        exit(1)
        
    print(f"Found {len(samples)} samples for {db_id}.")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Run baseline (no playbook)
    print("\n=== BASELINE CONDITION (No playbook) ===")
    # reset_playbook(db_id)
    baseline_records = run_experiment(db_id, samples, playbook_enabled=False)
    
    # Run ACE configuration
    print("\n=== ACE CONFIGURATION (Playbook growth enabled) ===")
    # reset_playbook(db_id)
    ace_records = run_experiment(db_id, samples, playbook_enabled=True)
    
    # Save results to output CSV file
    os.makedirs("results", exist_ok=True)
    csv_path = f"results/experiment_{timestamp}.csv"
    with open(csv_path, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["iteration", "ex_accuracy", "simple_acc", "moderate_acc", "challenging_acc", "playbook_entries", "playbook_enabled"])
        writer.writeheader()
        writer.writerows(baseline_records + ace_records)
    print(f"\nExperiment complete! Saved results to {csv_path}")
