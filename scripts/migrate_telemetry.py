import duckdb
from pathlib import Path

def migrate():
    db_path = Path("artifacts/metrics.duckdb")
    if not db_path.exists():
        print("Database not found, nothing to migrate.")
        return

    print(f"Connecting to {db_path}...")
    conn = duckdb.connect(str(db_path))
    
    # 1. Update metric_events
    cols_metric = [r[1] for r in conn.execute("PRAGMA table_info('metric_events')").fetchall()]
    if 'runtime_profile' not in cols_metric:
        print("Migrating metric_events...")
        conn.execute("ALTER TABLE metric_events ADD COLUMN runtime_profile VARCHAR DEFAULT 'unknown'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_profile ON metric_events (runtime_profile)")
    else:
        print("metric_events already up to date.")

    # 2. Update run_summaries
    cols_summary = [r[1] for r in conn.execute("PRAGMA table_info('run_summaries')").fetchall()]
    if 'runtime_profile' not in cols_summary:
        print("Migrating run_summaries...")
        conn.execute("ALTER TABLE run_summaries ADD COLUMN runtime_profile VARCHAR DEFAULT 'unknown'")
    else:
        print("run_summaries already up to date.")

    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
