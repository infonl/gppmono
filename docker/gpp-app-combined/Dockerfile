# syntax=docker/dockerfile:1
# Combined Dockerfile: FastAPI BFF with embedded Vue.js frontend
# Build context should be ./services (contains both gpp-app and gpp-app-fastapi)

# =============================================================================
# Frontend build stage - builds Vue.js app using Bun
# =============================================================================
FROM oven/bun:1-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY gpp-app/odpc.client/package.json gpp-app/odpc.client/bun.lockb* ./

# Install dependencies
RUN bun install --frozen-lockfile || bun install

# Copy frontend source
COPY gpp-app/odpc.client/ ./

# Build for production
RUN bun run build-only

# =============================================================================
# Python build stage
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files and README (needed for package build)
COPY gpp-app-fastapi/pyproject.toml gpp-app-fastapi/uv.lock* gpp-app-fastapi/README.md ./

# Install dependencies (no dev deps for production)
RUN uv sync --frozen --no-dev || uv sync --no-dev

# Copy application code
COPY gpp-app-fastapi/src/ ./src/

# =============================================================================
# Production stage
# =============================================================================
FROM python:3.12-slim AS production

# Build arguments for labeling
ARG COMMIT_HASH=""
ARG RELEASE=""

LABEL org.opencontainers.image.title="gpp-app-combined" \
      org.opencontainers.image.description="GPP App - FastAPI BFF with Vue.js frontend" \
      org.opencontainers.image.revision="${COMMIT_HASH}" \
      org.opencontainers.image.version="${RELEASE}"

WORKDIR /app

# Create non-root user
RUN useradd --create-home --uid 1000 --shell /bin/bash gpp-app && \
    mkdir -p /app/log /app/static && \
    chown -R gpp-app:gpp-app /app

# Copy virtual environment from builder
COPY --from=builder --chown=gpp-app:gpp-app /app/.venv /app/.venv

# Copy application code
COPY --from=builder --chown=gpp-app:gpp-app /app/src ./src

# Copy built frontend assets to static directory
COPY --from=frontend-builder --chown=gpp-app:gpp-app /frontend/dist ./static

# Set environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    LOG_FORMAT=json

VOLUME ["/app/log"]

USER gpp-app

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

EXPOSE 8000

CMD ["uvicorn", "gpp_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
