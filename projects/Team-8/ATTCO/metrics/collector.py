"""
Metrics Collector — async non-blocking metrics ingestion interface.
All ATTCO subsystems call collector.record() to emit metric events.
The collector buffers and flushes to MetricsStore without blocking callers.
"""
from __future__ import annotations

import asyncio

import structlog

from metrics.schema import MetricEvent
from metrics.store import MetricsStore

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """
    Non-blocking async metrics collector.
    Internally queues events and flushes them to MetricsStore via background task.
    """

    def __init__(self, store: MetricsStore, flush_interval_s: float = 5.0) -> None:
        self._store = store
        self._flush_interval = flush_interval_s
        self._queue: asyncio.Queue[MetricEvent] = asyncio.Queue(maxsize=50_000)
        self._running = False

    async def start(self) -> None:
        self._running = True
        asyncio.create_task(self._flush_loop(), name="metrics_flush")

    async def record(self, event: MetricEvent) -> None:
        try:
            from infrastructure.config.profile_manager import ProfileManager
            if event.runtime_profile is None:
                event = event.model_copy(update={"runtime_profile": ProfileManager.get_active_profile_name()})
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("metrics_queue_full", metric=event.metric_name)

    async def _flush_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._flush_interval)
            await self._drain()

    async def _drain(self) -> None:
        batch: list[MetricEvent] = []
        while not self._queue.empty():
            try:
                batch.append(self._queue.get_nowait())
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break
        for event in batch:
            try:
                self._store.write_event(event)
            except Exception:
                logger.exception("metrics_write_failed", metric=event.metric_name)
        if batch:
            logger.debug("metrics_flushed", count=len(batch))

    async def close(self) -> None:
        self._running = False
        await self._drain()
