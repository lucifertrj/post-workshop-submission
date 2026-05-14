import sqlite3
import json
import uuid
from datetime import datetime
from database import get_db
from core.variant_generator import generate_variants
from core.scorer import run_on_dataset, accuracy_score, llm_judge_score
from core.criteria_scorer import criteria_score
from core.ranker import rank_variants, store_best

def run_optimization(run_id):
    db = get_db()
    run = dict(db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone())
    db.execute("UPDATE runs SET status='running' WHERE id=?", (run_id,))
    db.commit()

    baseline_score = 0.5
    db.execute("UPDATE runs SET baseline_score=? WHERE id=?", (baseline_score, run_id))
    db.commit()

    score_history = [baseline_score]
    best_score = baseline_score

    for i in range(1, run["max_iterations"] + 1):
        db.execute("UPDATE runs SET iterations_run=? WHERE id=?", (i, run_id))
        db.commit()

        variants = generate_variants(run["base_prompt"], run["task_type"], run["task_name"], run["variants_per_iter"], str(score_history[-3:]))
        
        for v_text in variants:
            if run["mode"] == "dataset":
                dataset = json.loads(run["dataset_json"])
                outputs = run_on_dataset(v_text, dataset)
                score = accuracy_score(outputs)
            else:
                criteria = json.loads(run["criteria_json"])
                test_input = json.loads(run["dataset_json"])[0]["input"] if run["dataset_json"] != "[]" else "Test input"
                score = criteria_score(v_text, criteria, test_input)

            vid = f"var-{uuid.uuid4().hex[:8]}"
            db.execute("INSERT INTO prompt_variants (id, run_id, iteration, prompt_text, score, token_count, latency_ms, created_at) VALUES (?,?,?,?,?,?,?,?)",
                       (vid, run_id, i, v_text, score, len(v_text)//4, 300, datetime.utcnow().isoformat()))
            db.commit()
            score_history.append(score)

        if max(score_history) >= run["early_stop_threshold"]: break

    all_vars = [dict(r) for r in db.execute("SELECT * FROM prompt_variants WHERE run_id=?", (run_id,)).fetchall()]
    ranked = rank_variants(all_vars)
    if ranked: store_best(run_id, ranked[0])

    db.execute("UPDATE runs SET status='complete', completed_at=? WHERE id=?", (datetime.utcnow().isoformat(), run_id))
    db.commit()