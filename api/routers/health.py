"""
Health Router — liveness and readiness probes for the ATTCO API.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """Kubernetes liveness probe — returns 200 if process is alive."""
    return HealthResponse(status="ok", version="0.1.0")


@router.get("/ready", response_model=HealthResponse)
async def readiness() -> HealthResponse:
    """Kubernetes readiness probe — returns 200 when ready to serve traffic."""
    return HealthResponse(status="ready", version="0.1.0")
