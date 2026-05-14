"""Weights & Biases trace backend."""
from __future__ import annotations

import os
import wandb
import structlog
from tracing.schema import TraceEvent
from tracing.tracer import TracerBackend

logger = structlog.get_logger(__name__)

class WandbTracerBackend(TracerBackend):
    def __init__(self, project_name: str) -> None:
        self.project_name = project_name
        self.entity = os.getenv("WANDB_ENTITY") or None
        self._initialized = False

    async def emit(self, event: TraceEvent) -> None:
        try:
            if not self._initialized:
                import asyncio
                await asyncio.to_thread(
                    wandb.init,
                    project=self.project_name,
                    entity=self.entity,
                    id=event.run_id,
                    resume="allow",
                    reinit=True
                )
                self._initialized = True
                logger.info("wandb_initialized", project=self.project_name, entity=self.entity, run_id=event.run_id)

            import asyncio
            await asyncio.to_thread(wandb.log, {
                "event_class": event.event_class.value,
                "event_type": event.event_type,
                "step": event.step,
                "token_delta": event.token_delta,
                "latency_ms": event.latency_ms,
                "runtime_profile": event.runtime_profile,
                **event.payload
            })
        except Exception as e:
            logger.warning("wandb_emit_error", error=str(e))

    async def flush(self) -> None:
        pass

    async def close(self) -> None:
        if self._initialized:
            try:
                wandb.finish()
            except Exception:
                pass

