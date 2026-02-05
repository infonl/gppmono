"""Health check endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from woo_hoo import __version__
from woo_hoo.config import get_settings
from woo_hoo.models.responses import HealthResponse, ReadyResponse
from woo_hoo.services.openrouter import OpenRouterClient

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.

    Returns:
        Health status with service name and version
    """
    return HealthResponse(
        status="healthy",
        service="woo-hoo",
        version=__version__,
    )


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check() -> ReadyResponse:
    """Readiness check including OpenRouter connectivity.

    Returns:
        Readiness status with connectivity information
    """
    settings = get_settings()

    # Check if API key is configured
    if not settings.openrouter_api_key:
        return ReadyResponse(
            status="not_configured",
            openrouter_connected=False,
        )

    client = OpenRouterClient()
    try:
        connected = await client.check_connectivity()
        return ReadyResponse(
            status="ready" if connected else "degraded",
            openrouter_connected=connected,
        )
    finally:
        await client.close()
