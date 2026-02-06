"""Metadata proxy endpoints (including woo-hoo integration)."""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from gpp_app.auth.oidc import OdpcUser, get_current_user
from gpp_app.config import Settings, get_settings
from gpp_app.services.gpp_api_client import get_gpp_api_client
from gpp_app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class MetadataHealthResponse(BaseModel):
    """Response for metadata service health check."""

    available: bool
    message: str


class MetadataGenerateRequest(BaseModel):
    """Request to generate metadata for a document."""

    document_uuid: str


class MetadataGenerateResponse(BaseModel):
    """Response from metadata generation."""

    success: bool
    metadata: dict | None = None
    error: str | None = None


@router.get("/metadata/health", response_model=MetadataHealthResponse)
async def check_metadata_health(
    user: Annotated[OdpcUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MetadataHealthResponse:
    """Check if woo-hoo metadata service is available.

    Args:
        user: Current user
        settings: Application settings

    Returns:
        Health status of metadata service
    """
    if not settings.woo_hoo_base_url:
        return MetadataHealthResponse(
            available=False,
            message="woo-hoo service not configured",
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.woo_hoo_base_url}/health",
                timeout=settings.woo_hoo_health_timeout_seconds,
            )
            response.raise_for_status()

            data = response.json()
            return MetadataHealthResponse(
                available=data.get("status") == "healthy",
                message=f"woo-hoo version {data.get('version', 'unknown')}",
            )

    except httpx.HTTPError as e:
        logger.warning("woo_hoo_health_check_failed", error=str(e))
        return MetadataHealthResponse(
            available=False,
            message=f"Health check failed: {e}",
        )


@router.post("/metadata/generate/{document_uuid}", response_model=MetadataGenerateResponse)
async def generate_metadata(
    document_uuid: str,
    user: Annotated[OdpcUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MetadataGenerateResponse:
    """Generate metadata for a document using woo-hoo.

    Args:
        document_uuid: UUID of the document to generate metadata for
        user: Current user
        settings: Application settings

    Returns:
        Generated metadata or error
    """
    if not settings.woo_hoo_base_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="woo-hoo service not configured",
        )

    logger.info(
        "generate_metadata_start",
        document_uuid=document_uuid,
        user_id=user.id,
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.woo_hoo_base_url}/api/v1/metadata/generate-from-publicatiebank",
                json={"document_uuid": document_uuid},
                timeout=settings.woo_hoo_generate_timeout_seconds,
            )
            response.raise_for_status()

            data = response.json()

            logger.info(
                "generate_metadata_success",
                document_uuid=document_uuid,
                success=data.get("success"),
            )

            return MetadataGenerateResponse(
                success=data.get("success", False),
                metadata=data.get("suggestion", {}).get("metadata"),
                error=data.get("error"),
            )

    except httpx.HTTPStatusError as e:
        logger.error(
            "generate_metadata_http_error",
            document_uuid=document_uuid,
            status=e.response.status_code,
            error=str(e),
        )
        return MetadataGenerateResponse(
            success=False,
            error=f"HTTP error: {e.response.status_code}",
        )

    except httpx.HTTPError as e:
        logger.error(
            "generate_metadata_error",
            document_uuid=document_uuid,
            error=str(e),
        )
        return MetadataGenerateResponse(
            success=False,
            error=str(e),
        )


@router.get("/organisaties")
async def list_organisations(
    user: Annotated[OdpcUser, Depends(get_current_user)],
) -> JSONResponse:
    """List organisations.

    Args:
        user: Current user

    Returns:
        List of organisations
    """
    client = get_gpp_api_client(user)

    try:
        response = await client.get(
            "/api/v2/organisaties",
            action="list_organisations",
        )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
        )

    finally:
        await client.close()


@router.get("/informatiecategorieen")
async def list_information_categories(
    user: Annotated[OdpcUser, Depends(get_current_user)],
) -> JSONResponse:
    """List information categories.

    Args:
        user: Current user

    Returns:
        List of information categories
    """
    client = get_gpp_api_client(user)

    try:
        response = await client.get(
            "/api/v2/informatiecategorieen",
            action="list_categories",
        )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
        )

    finally:
        await client.close()


@router.get("/onderwerpen")
async def list_topics(
    user: Annotated[OdpcUser, Depends(get_current_user)],
) -> JSONResponse:
    """List topics.

    Args:
        user: Current user

    Returns:
        List of topics
    """
    client = get_gpp_api_client(user)

    try:
        response = await client.get(
            "/api/v2/onderwerpen",
            action="list_topics",
        )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
        )

    finally:
        await client.close()
