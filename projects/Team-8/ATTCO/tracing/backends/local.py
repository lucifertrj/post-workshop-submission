"""Local file-based trace backend."""
from __future__ import annotations
from pathlib import Path
from tracing.schema import TraceEvent
import structlog

logger = structlog.get_logger(__name__)


class LocalTracerBackend:
    def __init__(self, output_dir: Path) -> None:
        self._dir = Path(output_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    async def emit(self, event: TraceEvent) -> None:
        path = self._dir / f"{event.run_id}.jsonl"
        with open(path, "a") as f:
            f.write(event.model_dump_json() + "\n")

    async def flush(self) -> None:
        pass

    async def close(self) -> None:
        pass
