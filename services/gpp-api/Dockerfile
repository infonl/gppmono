# syntax=docker/dockerfile:1

# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files and README (needed for package build)
COPY pyproject.toml uv.lock* README.md ./

# Install dependencies (no dev deps for production)
RUN uv sync --frozen --no-dev || uv sync --no-dev

# Copy application code
COPY src/ ./src/

# Test stage (for running tests in Docker)
FROM builder AS test

# Install dev dependencies for testing
RUN uv sync --frozen || uv sync

# Copy test files
COPY tests/ ./tests/

# Run tests
CMD ["uv", "run", "pytest", "tests", "-v"]

# Production stage
FROM python:3.12-slim AS production

# Build arguments for labeling
ARG COMMIT_HASH=""
ARG RELEASE=""

# Labels following OCI conventions
LABEL org.opencontainers.image.title="gpp-api" \
      org.opencontainers.image.description="GPP API - FastAPI backend for publication management" \
      org.opencontainers.image.url="https://github.com/GPP-Woo/GPP-publicatiebank" \
      org.opencontainers.image.source="https://github.com/GPP-Woo/GPP-publicatiebank" \
      org.opencontainers.image.documentation="https://github.com/GPP-Woo/GPP-publicatiebank" \
      org.opencontainers.image.vendor="GPP-Woo" \
      org.opencontainers.image.licenses="EUPL-1.2" \
      org.opencontainers.image.revision="${COMMIT_HASH}" \
      org.opencontainers.image.version="${RELEASE}"

WORKDIR /app

# Create non-root user (following GPP pattern)
RUN useradd --create-home --uid 1000 --shell /bin/bash gpp-api && \
    mkdir -p /app/log && \
    chown -R gpp-api:gpp-api /app

# Copy virtual environment from builder
COPY --from=builder --chown=gpp-api:gpp-api /app/.venv /app/.venv

# Copy application code
COPY --from=builder --chown=gpp-api:gpp-api /app/src ./src

# Set environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    # Default production settings
    LOG_LEVEL=INFO \
    LOG_FORMAT=json

# Volume for logs (matches GPP pattern)
VOLUME ["/app/log"]

# Switch to non-root user
USER gpp-api

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

EXPOSE 8000

CMD ["uvicorn", "gpp_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
