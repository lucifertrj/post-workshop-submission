"""
Core Tracer Interface — the single emit surface for all ATTCO trace events.
All subsystems call tracer.emit(event). Backend routing is internal.
"""
from __future__ import annotations

import asyncio
from typing import Protocol, runtime_checkable

import structlog

from tracing.schema import TraceEvent

logger = structlog.get_logger(__name__)


@runtime_checkable
class TracerBackend(Protocol):
    """Backend protocol — all trace backends must satisfy this interface."""

    async def emit(self, event: TraceEvent) -> None: ...
    async def flush(self) -> None: ...
    async def close(self) -> None: ...


class Tracer:
    """
    Central tracer. Routes TraceEvents to all registered backends.
    All emit calls are fire-and-forget async — never blocks the hot path.
    """

    def __init__(self, backends: list[TracerBackend]) -> None:
        self._backends = backends
        self._queue: asyncio.Queue[TraceEvent] = asyncio.Queue(maxsize=10_000)
        self._running = False

    async def start(self) -> None:
        self._running = True
        asyncio.create_task(self._drain_loop(), name="tracer_drain")

    async def emit(self, event: TraceEvent) -> None:
        try:
            from infrastructure.config.profile_manager import ProfileManager
            
            # Inject active profile if not already set
            if event.runtime_profile is None:
                # TraceEvent is frozen, so we need to create a new one with the profile
                event = event.model_copy(update={"runtime_profile": ProfileManager.get_active_profile_name()})
                
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("tracer_queue_full", event_class=event.event_class)

    async def _drain_loop(self) -> None:
        try:
            while self._running:
                try:
                    event = await self._queue.get()
                except RuntimeError: # Loop closed
                    break
                    
                for backend in self._backends:
                    try:
                        await backend.emit(event)
                    except Exception:
                        # Isolation: Telemetry failure must never crash the runtime
                        logger.exception("tracer_backend_error", backend=type(backend).__name__)
                
                try:
                    self._queue.task_done()
                except ValueError:
                    pass
        except Exception:
            logger.exception("tracer_critical_failure")
        finally:
            self._running = False

    async def flush(self) -> None:
        await self._queue.join()
        for backend in self._backends:
            await backend.flush()

    async def close(self) -> None:
        self._running = False
        await self.flush()
        for backend in self._backends:
            await backend.close()

# Helper to initialize default backends
def _get_default_backends() -> list[TracerBackend]:
    from infrastructure.config.loader import ConfigLoader
    from tracing.backends.local import LocalTracerBackend
    from tracing.backends.wandb_backend import WandbTracerBackend
    from pathlib import Path
    import os
    
    ConfigLoader.load()
    backends: list[TracerBackend] = [LocalTracerBackend(Path("artifacts/traces"))]
    
    if os.getenv("WANDB_API_KEY") and os.getenv("WANDB_PROJECT"):
        backends.append(WandbTracerBackend(os.getenv("WANDB_PROJECT", "ATTCO")))
        
    return backends

# Global tracer instance
global_tracer = Tracer(_get_default_backends())
