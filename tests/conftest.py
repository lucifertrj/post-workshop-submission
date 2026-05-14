"""
Shared pytest fixtures for ATTCO test suite.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from metrics.store import MetricsStore
from metrics.collector import MetricsCollector
from tracing.tracer import Tracer
from tracing.backends.local import LocalTracerBackend


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def tmp_metrics_store(tmp_path: Path) -> MetricsStore:
    db = tmp_path / "test_metrics.duckdb"
    store = MetricsStore(db_path=db)
    yield store
    store.close()


@pytest.fixture
async def metrics_collector(tmp_metrics_store: MetricsStore) -> MetricsCollector:
    collector = MetricsCollector(store=tmp_metrics_store)
    await collector.start()
    yield collector
    await collector.close()


@pytest.fixture
def local_tracer_backend(tmp_path: Path) -> LocalTracerBackend:
    return LocalTracerBackend(output_dir=tmp_path / "traces")


@pytest.fixture
async def tracer(local_tracer_backend: LocalTracerBackend) -> Tracer:
    t = Tracer(backends=[local_tracer_backend])
    await t.start()
    yield t
    await t.close()
