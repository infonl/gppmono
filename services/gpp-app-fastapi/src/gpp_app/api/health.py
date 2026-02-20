"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from gpp_app import __version__

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic liveness check.

    Returns:
        HealthResponse indicating service is running
    """
    return HealthResponse(
        status="healthy",
        service="gpp-app",
        version=__version__,
    )
