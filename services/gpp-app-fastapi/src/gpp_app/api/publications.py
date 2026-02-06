"""Publication proxy endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from gpp_app.auth.oidc import OdpcUser, get_current_user
from gpp_app.services.gpp_api_client import get_gpp_api_client

router = APIRouter()


@router.get("/publicaties")
async def list_publications(
    user: Annotated[OdpcUser, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
) -> JSONResponse:
    """List publications.

    Proxies to gpp-api and filters based on user permissions.

    Args:
        user: Current user
        page: Page number
        page_size: Items per page
        status: Optional status filter

    Returns:
        List of publications
    """
    client = get_gpp_api_client(user)

    try:
        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
        }
        if status:
            params["status"] = status

        response = await client.get(
            "/api/v2/publicaties",
            params=params,
            action="list_publications",
        )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
        )

    finally:
        await client.close()


@router.get("/publicaties/{uuid}")
async def get_publication(
    uuid: str,
    user: Annotated[OdpcUser, Depends(get_current_user)],
) -> JSONResponse:
    """Get a single publication.

    Args:
        uuid: Publication UUID
        user: Current user

    Returns:
        Publication details
    """
    client = get_gpp_api_client(user)

    try:
        response = await client.get(
            f"/api/v2/publicaties/{uuid}",
            action=f"get_publication:{uuid}",
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Publication not found",
            )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
        )

    finally:
        await client.close()


@router.post("/publicaties")
async def create_publication(
    user: Annotated[OdpcUser, Depends(get_current_user)],
    body: dict[str, Any],
) -> JSONResponse:
    """Create a new publication.

    Args:
        user: Current user
        body: Publication data

    Returns:
        Created publication
    """
    client = get_gpp_api_client(user)

    try:
        response = await client.post(
            "/api/v2/publicaties",
            json=body,
            action="create_publication",
        )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
        )

    finally:
        await client.close()


@router.put("/publicaties/{uuid}")
async def update_publication(
    uuid: str,
    user: Annotated[OdpcUser, Depends(get_current_user)],
    body: dict[str, Any],
) -> JSONResponse:
    """Update a publication.

    Args:
        uuid: Publication UUID
        user: Current user
        body: Publication data

    Returns:
        Updated publication
    """
    client = get_gpp_api_client(user)

    try:
        response = await client.put(
            f"/api/v2/publicaties/{uuid}",
            json=body,
            action=f"update_publication:{uuid}",
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Publication not found",
            )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
        )

    finally:
        await client.close()


@router.delete("/publicaties/{uuid}")
async def delete_publication(
    uuid: str,
    user: Annotated[OdpcUser, Depends(get_current_user)],
) -> JSONResponse:
    """Delete a publication.

    Args:
        uuid: Publication UUID
        user: Current user

    Returns:
        Empty response on success
    """
    client = get_gpp_api_client(user)

    try:
        response = await client.delete(
            f"/api/v2/publicaties/{uuid}",
            action=f"delete_publication:{uuid}",
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Publication not found",
            )

        return JSONResponse(
            content=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )

    finally:
        await client.close()


@router.post("/publicaties/{uuid}/publish")
async def publish_publication(
    uuid: str,
    user: Annotated[OdpcUser, Depends(get_current_user)],
) -> JSONResponse:
    """Publish a publication.

    Args:
        uuid: Publication UUID
        user: Current user

    Returns:
        Updated publication
    """
    client = get_gpp_api_client(user)

    try:
        response = await client.post(
            f"/api/v2/publicaties/{uuid}/publish",
            action=f"publish_publication:{uuid}",
        )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
        )

    finally:
        await client.close()


@router.post("/publicaties/{uuid}/revoke")
async def revoke_publication(
    uuid: str,
    user: Annotated[OdpcUser, Depends(get_current_user)],
) -> JSONResponse:
    """Revoke a publication.

    Args:
        uuid: Publication UUID
        user: Current user

    Returns:
        Updated publication
    """
    client = get_gpp_api_client(user)

    try:
        response = await client.post(
            f"/api/v2/publicaties/{uuid}/revoke",
            action=f"revoke_publication:{uuid}",
        )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
        )

    finally:
        await client.close()
