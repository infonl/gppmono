"""Document proxy endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from gpp_app.auth.oidc import OdpcUser, get_current_user
from gpp_app.services.gpp_api_client import GppApiClient, get_gpp_api_client

router = APIRouter()


@router.get("/documenten")
async def list_documents(
    user: Annotated[OdpcUser, Depends(get_current_user)],
    publicatie: str | None = Query(None, description="Filter by publication UUID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> JSONResponse:
    """List documents.

    Args:
        user: Current user
        publicatie: Optional publication UUID filter
        page: Page number
        page_size: Items per page

    Returns:
        List of documents
    """
    client = get_gpp_api_client(user)

    try:
        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
        }
        if publicatie:
            params["publicatie"] = publicatie

        response = await client.get(
            "/api/v2/documenten",
            params=params,
            action="list_documents",
        )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
        )

    finally:
        await client.close()


@router.get("/documenten/{uuid}")
async def get_document(
    uuid: str,
    user: Annotated[OdpcUser, Depends(get_current_user)],
) -> JSONResponse:
    """Get a single document.

    Args:
        uuid: Document UUID
        user: Current user

    Returns:
        Document details
    """
    client = get_gpp_api_client(user)

    try:
        response = await client.get(
            f"/api/v2/documenten/{uuid}",
            action=f"get_document:{uuid}",
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
        )

    finally:
        await client.close()


@router.post("/documenten")
async def create_document(
    user: Annotated[OdpcUser, Depends(get_current_user)],
    body: dict[str, Any],
) -> JSONResponse:
    """Create a new document.

    Args:
        user: Current user
        body: Document data

    Returns:
        Created document
    """
    client = get_gpp_api_client(user)

    try:
        response = await client.post(
            "/api/v2/documenten",
            json=body,
            action="create_document",
        )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
        )

    finally:
        await client.close()


@router.put("/documenten/{uuid}")
async def update_document(
    uuid: str,
    user: Annotated[OdpcUser, Depends(get_current_user)],
    body: dict[str, Any],
) -> JSONResponse:
    """Update a document.

    Args:
        uuid: Document UUID
        user: Current user
        body: Document data

    Returns:
        Updated document
    """
    client = get_gpp_api_client(user)

    try:
        response = await client.put(
            f"/api/v2/documenten/{uuid}",
            json=body,
            action=f"update_document:{uuid}",
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
        )

    finally:
        await client.close()


@router.delete("/documenten/{uuid}")
async def delete_document(
    uuid: str,
    user: Annotated[OdpcUser, Depends(get_current_user)],
) -> JSONResponse:
    """Delete a document.

    Args:
        uuid: Document UUID
        user: Current user

    Returns:
        Empty response on success
    """
    client = get_gpp_api_client(user)

    try:
        response = await client.delete(
            f"/api/v2/documenten/{uuid}",
            action=f"delete_document:{uuid}",
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        return JSONResponse(
            content=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )

    finally:
        await client.close()
