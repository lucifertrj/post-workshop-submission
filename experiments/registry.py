"""
Experiment Registry — registers, versions, and retrieves experiments.
Every experiment run is assigned a unique ID and versioned with git SHA + timestamp.
"""
from __future__ import annotations

import hashlib
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


import json
from pathlib import Path

@dataclass
class ExperimentRecord:
    experiment_id: str
    name: str
    config_snapshot: dict[str, Any]
    git_sha: str
    signature_hash: str
    created_at: datetime = field(default_factory=datetime.utcnow)

class ExperimentRegistry:
    """In-process experiment registry with versioning support."""

    def __init__(self, artifacts_dir: str = "artifacts") -> None:
        self._records: dict[str, ExperimentRecord] = {}
        self.artifacts_dir = Path(artifacts_dir)

    def register(self, name: str, config: dict[str, Any]) -> ExperimentRecord:
        experiment_id = str(uuid.uuid4())
        sha = _git_sha()
        
        # Compute execution signature
        config_str = json.dumps(config, sort_keys=True)
        sig_str = f"{sha}-{config_str}"
        signature_hash = hashlib.sha256(sig_str.encode()).hexdigest()
        
        record = ExperimentRecord(
            experiment_id=experiment_id,
            name=name,
            config_snapshot=config,
            git_sha=sha,
            signature_hash=signature_hash
        )
        self._records[experiment_id] = record
        
        # Artifact tracking
        exp_dir = self.artifacts_dir / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        
        with open(exp_dir / "config_snapshot.json", "w") as f:
            json.dump(config, f, indent=2)
            
        with open(exp_dir / "git_sha.txt", "w") as f:
            f.write(sha)
            
        with open(exp_dir / "signature.json", "w") as f:
            json.dump({"experiment_id": experiment_id, "signature_hash": signature_hash, "git_sha": sha}, f, indent=2)

        logger.info("experiment_registered", id=experiment_id, name=name, sha=sha, signature=signature_hash)
        return record

    def get(self, experiment_id: str) -> ExperimentRecord | None:
        return self._records.get(experiment_id)

    def list_all(self) -> list[ExperimentRecord]:
        return list(self._records.values())
