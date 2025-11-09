"""FastAPI middleware for request tracing and metrics"""

import uuid
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from gerald_gateway.infrastructure.observability.metrics import request_duration_histogram


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for distributed tracing"""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record HTTP request metrics"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time
        request_duration_histogram.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).observe(duration)

        return response
