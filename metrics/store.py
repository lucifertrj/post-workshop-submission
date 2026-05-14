"""
Metrics Store — DuckDB-backed queryable store for all metric events.
Supports local analytical queries and Parquet export.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import structlog

from metrics.schema import MetricEvent, RunSummary

logger = structlog.get_logger(__name__)

_DEFAULT_DB = Path("artifacts/metrics.duckdb")


class MetricsStore:
    """
    Async-compatible DuckDB metrics store.
    DuckDB connections are thread-safe for read operations.
    Write serialization is handled by the caller (MetricsCollector).
    """

    def __init__(self, db_path: Path = _DEFAULT_DB) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = duckdb.connect(str(db_path))
            self._init_schema()
        except duckdb.IOException as e:
            if "The process cannot access the file" in str(e):
                logger.warning("metrics_store_locked", path=str(db_path), error="file_in_use")
                # Fallback to read-only if possible, or just fail gracefully
                try:
                    self._conn = duckdb.connect(str(db_path), read_only=True)
                    logger.info("metrics_store_readonly_fallback")
                except:
                    raise e
            else:
                raise e

    def _init_schema(self) -> None:
        # Check if we have write access
        is_readonly = False
        try:
            res = self._conn.execute("SELECT access_mode FROM duckdb_databases() WHERE database_name = 'metrics'").fetchone()
            if not res: # default database
                res = self._conn.execute("SELECT access_mode FROM duckdb_databases() LIMIT 1").fetchone()
            is_readonly = res[0] == 'READ_ONLY' if res else False
        except:
            is_readonly = True # Assume readonly if check fails

        if is_readonly:
            logger.info("skipping_migration_readonly")
            return

        # 1. Metric Events Table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS metric_events (
                event_id VARCHAR PRIMARY KEY,
                experiment_id VARCHAR NOT NULL,
                run_id VARCHAR NOT NULL,
                question_id VARCHAR NOT NULL,
                metric_name VARCHAR NOT NULL,
                value DOUBLE NOT NULL,
                unit VARCHAR NOT NULL,
                step INTEGER,
                timestamp_utc TIMESTAMP NOT NULL,
                tags JSON,
                runtime_profile VARCHAR DEFAULT 'unknown'
            )
        """)
        
        # Robust migration for metric_events
        cols_metric = [r[1] for r in self._conn.execute("PRAGMA table_info('metric_events')").fetchall()]
        if 'runtime_profile' not in cols_metric:
            self._conn.execute("ALTER TABLE metric_events ADD COLUMN runtime_profile VARCHAR DEFAULT 'unknown'")
            logger.info("migration_applied", table="metric_events", column="runtime_profile")
            
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_profile ON metric_events (runtime_profile)")

        # 2. Run Summaries Table
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS run_summaries (
                run_id VARCHAR PRIMARY KEY,
                experiment_id VARCHAR NOT NULL,
                total_questions INTEGER,
                avg_accuracy DOUBLE,
                avg_latency_ms DOUBLE,
                avg_latency_p95 DOUBLE,
                avg_tokens DOUBLE,
                avg_reasoning_depth DOUBLE,
                avg_tool_calls DOUBLE,
                efficiency_ratio DOUBLE,
                completed_at TIMESTAMP,
                runtime_profile VARCHAR DEFAULT 'unknown'
            )
        """)
        
        # Robust migration for run_summaries - handle rename or missing
        cols_summary = [r[1] for r in self._conn.execute("PRAGMA table_info('run_summaries')").fetchall()]
        if 'avg_accuracy' not in cols_summary and 'accuracy' in cols_summary:
            # Drop and recreate if schema changed significantly
            self._conn.execute("DROP TABLE run_summaries")
            self._init_schema() # Recursive call will skip DROP because of IF NOT EXISTS
            return
        
        if 'runtime_profile' not in cols_summary:
            self._conn.execute("ALTER TABLE run_summaries ADD COLUMN runtime_profile VARCHAR DEFAULT 'unknown'")
            logger.info("migration_applied", table="run_summaries", column="runtime_profile")

        logger.info("metrics_store_initialized")

    def write_event(self, event: MetricEvent) -> None:
        self._conn.execute("""
            INSERT OR REPLACE INTO metric_events VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, [
            str(event.event_id), event.experiment_id, event.run_id,
            event.question_id, event.metric_name, event.value, event.unit,
            event.step, event.timestamp_utc, str(event.tags), event.runtime_profile
        ])

    def write_summary(self, summary: RunSummary) -> None:
        self._conn.execute("""
            INSERT OR REPLACE INTO run_summaries VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, [
            summary.run_id, summary.experiment_id, summary.total_questions,
            summary.avg_accuracy, summary.avg_latency_ms,
            summary.avg_latency_p95, summary.avg_tokens,
            summary.avg_reasoning_depth, summary.avg_tool_calls,
            summary.efficiency_ratio, summary.completed_at, summary.runtime_profile
        ])

    def export_parquet(self, out_path: Path) -> None:
        self._conn.execute(f"COPY metric_events TO '{out_path}' (FORMAT PARQUET)")
        logger.info("metrics_exported_parquet", path=str(out_path))

    def close(self) -> None:
        self._conn.close()
