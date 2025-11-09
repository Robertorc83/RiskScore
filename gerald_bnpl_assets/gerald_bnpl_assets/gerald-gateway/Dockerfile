# Multi-stage Dockerfile for production deployment

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install poetry
RUN pip install --no-cache-dir poetry==1.7.0

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Export dependencies to requirements.txt (faster for Docker caching)
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY gerald_gateway/ ./gerald_gateway/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run with uvicorn
CMD ["uvicorn", "gerald_gateway.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
