"""Information category endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/informatiecategorieen")
async def list_categories() -> dict:
    """List all information categories.

    Returns:
        List of information categories
    """
    # TODO: Implement with database query
    return {"count": 0, "results": []}


@router.get("/informatiecategorieen/{uuid}")
async def get_category(uuid: str) -> dict:
    """Get a single information category by UUID.

    Args:
        uuid: Category UUID

    Returns:
        Category details
    """
    # TODO: Implement with database query
    return {"uuid": uuid}
