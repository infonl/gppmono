"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from gpp_api import __version__

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    service: str
    version: str


class ReadyResponse(BaseModel):
    """Readiness check response model."""

    status: str
    service: str
    version: str
    database: str
    redis: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic liveness check.

    Returns:
        HealthResponse indicating service is running
    """
    return HealthResponse(
        status="healthy",
        service="gpp-api",
        version=__version__,
    )


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check() -> ReadyResponse:
    """Readiness check with dependency verification.

    Checks database and Redis connectivity.

    Returns:
        ReadyResponse with status of each dependency
    """
    # TODO: Implement actual database and Redis connectivity checks
    database_status = "not_checked"
    redis_status = "not_checked"

    return ReadyResponse(
        status="ready",
        service="gpp-api",
        version=__version__,
        database=database_status,
        redis=redis_status,
    )
