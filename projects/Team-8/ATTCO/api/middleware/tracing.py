"""
Tracing Middleware — injects request-scoped trace context into every request.
"""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """Attaches a unique trace_id to every incoming request."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        trace_id = str(uuid.uuid4())
        start = time.perf_counter()

        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            method=request.method,
            path=request.url.path,
        )

        response: Response = await call_next(request)  # type: ignore[operator]

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "http_request_completed",
            status_code=response.status_code,
            latency_ms=round(elapsed_ms, 2),
        )

        response.headers["X-Trace-Id"] = trace_id
        structlog.contextvars.clear_contextvars()
        return response
