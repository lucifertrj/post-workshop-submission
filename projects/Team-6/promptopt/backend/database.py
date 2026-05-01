import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "promptopt.db")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY, task_name TEXT, task_type TEXT, mode TEXT,
            base_prompt TEXT, scorer TEXT, max_iterations INTEGER,
            early_stop_threshold REAL, variants_per_iter INTEGER,
            dataset_json TEXT, criteria_json TEXT, status TEXT DEFAULT 'queued',
            best_score REAL, baseline_score REAL, best_prompt TEXT,
            iterations_run INTEGER DEFAULT 0, token_count INTEGER DEFAULT 0,
            latency_ms INTEGER DEFAULT 0, failure_reason TEXT,
            created_at TEXT, completed_at TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS prompt_variants (
            id TEXT PRIMARY KEY, run_id TEXT, iteration INTEGER,
            prompt_text TEXT, score REAL, token_count INTEGER,
            latency_ms INTEGER, diff_json TEXT, created_at TEXT,
            FOREIGN KEY(run_id) REFERENCES runs(id))""")
        conn.commit()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn