"""Organisation endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/organisaties")
async def list_organisations() -> dict:
    """List all organisations.

    Returns:
        List of organisations
    """
    # TODO: Implement with database query
    return {"count": 0, "results": []}


@router.get("/organisaties/{uuid}")
async def get_organisation(uuid: str) -> dict:
    """Get a single organisation by UUID.

    Args:
        uuid: Organisation UUID

    Returns:
        Organisation details
    """
    # TODO: Implement with database query
    return {"uuid": uuid}
