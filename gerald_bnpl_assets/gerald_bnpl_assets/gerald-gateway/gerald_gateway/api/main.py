"""FastAPI application factory"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from gerald_gateway.api.middleware import RequestIDMiddleware, MetricsMiddleware
from gerald_gateway.api.v1 import decision, plan, history
from gerald_gateway.infrastructure.observability.logging import setup_logging
from gerald_gateway.config import settings

# Setup structured logging
setup_logging(settings.log_level)


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Gerald BNPL Gateway",
        description="Credit decision and repayment plan service",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add middleware (order matters: last added = first executed)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # Health check endpoint
    @app.get("/health")
    def health_check():
        return {"status": "ok", "service": settings.service_name}

    # Prometheus metrics endpoint
    @app.get("/metrics")
    def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # Register API routers
    app.include_router(decision.router, prefix="/v1", tags=["decisions"])
    app.include_router(plan.router, prefix="/v1", tags=["plans"])
    app.include_router(history.router, prefix="/v1", tags=["history"])

    return app


app = create_app()
