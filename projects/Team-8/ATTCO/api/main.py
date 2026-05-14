"""
ATTCO — Adaptive Test-Time Compute Optimization
FastAPI Application Entrypoint
"""

from __future__ import annotations

import asyncio
import logging

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.tracing import TracingMiddleware
from api.routers import benchmarks, experiments, health, metrics

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="ATTCO Research Platform API",
    description="Adaptive Test-Time Compute Optimization — Inference Research Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TracingMiddleware)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(benchmarks.router, prefix="/api/v1/benchmarks", tags=["benchmarks"])
app.include_router(experiments.router, prefix="/api/v1/experiments", tags=["experiments"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("attco_api_started", version="0.1.0")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("attco_api_stopped")


def start() -> None:
    """Entrypoint for `attco-api` CLI command."""
    # uvloop is not natively supported on Windows, using standard asyncio loop
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
