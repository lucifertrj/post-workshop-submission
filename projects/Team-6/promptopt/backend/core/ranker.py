import sqlite3
from datetime import datetime
from database import get_db

def rank_variants(variants):
    return sorted(variants, key=lambda v: (-v["score"], v["token_count"], v["latency_ms"]))

def store_best(run_id, best):
    db = get_db()
    db.execute("""UPDATE runs SET best_prompt=?, best_score=?, token_count=?, latency_ms=?, status='complete', completed_at=? WHERE id=?""",
               (best["prompt_text"], best["score"], best["token_count"], best["latency_ms"], datetime.utcnow().isoformat(), run_id))
    db.commit()