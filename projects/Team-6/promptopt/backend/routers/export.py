from fastapi import APIRouter, HTTPException
from database import get_db
from datetime import datetime

router = APIRouter(prefix="/runs", tags=["export"])

@router.get("/{run_id}/export")
def export_run(run_id: str, format: str = "text"):
    db = get_db()
    r = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not r: raise HTTPException(404, "Run not found")
    if format == "json": return dict(r)
    return {"prompt": r["best_prompt"] or r["base_prompt"]}

@router.get("/{run_id}/versions")
def get_versions(run_id: str):
    db = get_db()
    rows = db.execute("SELECT * FROM prompt_variants WHERE run_id=? ORDER BY score DESC", (run_id,)).fetchall()
    return [{"id": r["id"], "version": i+1, "label": f"Iteration {r['iteration']}", **dict(r)} for i, r in enumerate(rows)]

@router.post("/registry")
def save_to_registry(run_id: str):
    return {"success": True, "message": "Saved to registry"}

@router.get("/registry")
def get_registry(status: str = None):
    db = get_db()
    q = "SELECT * FROM runs WHERE best_prompt IS NOT NULL"
    p = []
    if status: q += " AND status=?"; p.append(status)
    return [dict(r) for r in db.execute(q, p).fetchall()]