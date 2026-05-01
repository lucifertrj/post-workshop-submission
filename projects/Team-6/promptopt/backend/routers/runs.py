from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
from core.job_initializer import RunConfig
from database import get_db
from core.optimizer import run_optimization
import uuid
from datetime import datetime
import json

router = APIRouter(prefix="/runs", tags=["runs"])

@router.post("/")
def create_run(config: RunConfig, background_tasks: BackgroundTasks):
    db = get_db()
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()
    db.execute("""INSERT INTO runs (id, task_name, task_type, mode, base_prompt, scorer,
                 max_iterations, early_stop_threshold, variants_per_iter,
                 dataset_json, criteria_json, status, created_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (run_id, config.task_name, config.task_type, config.mode, config.base_prompt,
                config.scorer, config.max_iterations, config.early_stop_threshold,
                config.variants_per_iter, json.dumps(config.dataset or []),
                json.dumps(config.criteria or []), "queued", now))
    db.commit()
    background_tasks.add_task(run_optimization, run_id)
    return {"id": run_id, "status": "queued", "created_at": now}

@router.get("/")
def list_runs(status: Optional[str]=None, mode: Optional[str]=None, task_type: Optional[str]=None):
    db = get_db()
    q = "SELECT * FROM runs WHERE 1=1 ORDER BY created_at DESC"
    p = []
    if status: q += " AND status=?"; p.append(status)
    if mode: q += " AND mode=?"; p.append(mode)
    if task_type: q += " AND task_type=?"; p.append(task_type)
    return [dict(r) for r in db.execute(q, p).fetchall()]

@router.get("/{run_id}")
def get_run(run_id: str):
    db = get_db()
    r = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not r: raise HTTPException(404, "Run not found")
    return dict(r)

@router.delete("/{run_id}")
def cancel_run(run_id: str):
    db = get_db()
    db.execute("UPDATE runs SET status='failed', failure_reason='Cancelled by user', completed_at=? WHERE id=? AND status IN ('queued','running')",
               (datetime.utcnow().isoformat(), run_id))
    db.commit()
    return {"success": True}

@router.get("/{run_id}/variants")
def get_variants(run_id: str):
    db = get_db()
    return [dict(r) for r in db.execute("SELECT * FROM prompt_variants WHERE run_id=? ORDER BY iteration ASC", (run_id,)).fetchall()]