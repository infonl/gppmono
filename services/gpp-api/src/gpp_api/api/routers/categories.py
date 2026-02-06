"""Information category endpoints."""

from __future__ import annotations

import uuid as uuid_module
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from gpp_api.api.deps import get_db
from gpp_api.db.models import InformationCategory

router = APIRouter()


class InformationCategoryResponse(BaseModel):
    """Response model for an information category."""

    uuid: uuid_module.UUID
    identifier: str
    naam: str
    naam_meervoud: str = Field(serialization_alias="naamMeervoud")
    definitie: str
    omschrijving: str
    oorsprong: str
    order: int
    bron_bewaartermijn: str = Field(serialization_alias="bronBewaartermijn")
    selectiecategorie: str
    archiefnominatie: str
    bewaartermijn: int
    toelichting_bewaartermijn: str = Field(serialization_alias="toelichtingBewaartermijn")

    class Config:
        from_attributes = True
        populate_by_name = True


class InformationCategoryListResponse(BaseModel):
    """Response model for list of information categories."""

    count: int
    results: list[InformationCategoryResponse]


@router.get("/informatiecategorieen", response_model=InformationCategoryListResponse)
async def list_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InformationCategoryListResponse:
    """List all information categories.

    Args:
        db: Database session

    Returns:
        List of information categories
    """
    query = select(InformationCategory).order_by(InformationCategory.order, InformationCategory.naam)

    # Get count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    count = count_result.scalar() or 0

    # Get results
    result = await db.execute(query)
    categories = result.scalars().all()

    return InformationCategoryListResponse(
        count=count,
        results=[InformationCategoryResponse.model_validate(cat) for cat in categories],
    )


@router.get("/informatiecategorieen/{cat_uuid}", response_model=InformationCategoryResponse)
async def get_category(
    cat_uuid: uuid_module.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InformationCategoryResponse:
    """Get a single information category by UUID.

    Args:
        cat_uuid: Category UUID
        db: Database session

    Returns:
        Category details
    """
    query = select(InformationCategory).where(InformationCategory.uuid == cat_uuid)
    result = await db.execute(query)
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Information category with UUID {cat_uuid} not found",
        )

    return InformationCategoryResponse.model_validate(category)
