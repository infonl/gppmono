"""Publication endpoints using SQLAlchemy models."""

from __future__ import annotations

import uuid as uuid_module
from datetime import datetime, date, timezone
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from gpp_api.api.deps import get_db
from gpp_api.db.models import (
    Publication,
    PublicationIdentifier,
    PublicationStatus,
    Organisation,
    InformationCategory,
    Topic,
    OrganisationMember,
    OrganisationUnit,
)

router = APIRouter()


# Pydantic models for request/response
class EigenaarResponse(BaseModel):
    """Owner response model."""

    identifier: str
    weergaveNaam: str

    model_config = ConfigDict(from_attributes=True)


class EigenaarGroepResponse(BaseModel):
    """Owner group response model."""

    identifier: str
    weergaveNaam: str

    model_config = ConfigDict(from_attributes=True)


class KenmerkModel(BaseModel):
    """Identifier model."""

    kenmerk: str
    bron: str

    model_config = ConfigDict(from_attributes=True)


class PublicationCreate(BaseModel):
    """Request model for creating a publication."""

    publisher: str = ""
    verantwoordelijke: str = ""
    officieleTitel: str
    verkorteTitel: str = ""
    omschrijving: str = ""
    publicatiestatus: str = "concept"
    informatieCategorieen: list[str] = []
    onderwerpen: list[str] = []
    eigenaarGroep: dict | None = None
    kenmerken: list[KenmerkModel] = []
    datumBeginGeldigheid: str | None = None
    datumEindeGeldigheid: str | None = None
    bronBewaartermijn: str = ""
    selectiecategorie: str = ""
    archiefnominatie: str = ""
    toelichtingBewaartermijn: str = ""


class PublicationResponse(BaseModel):
    """Response model for a publication."""

    uuid: str
    publisher: str
    verantwoordelijke: str
    officieleTitel: str
    verkorteTitel: str
    omschrijving: str
    publicatiestatus: str
    informatieCategorieen: list[str]
    onderwerpen: list[str]
    eigenaar: EigenaarResponse | None = None
    eigenaarGroep: EigenaarGroepResponse | None = None
    registratiedatum: str
    laatstGewijzigdDatum: str
    kenmerken: list[KenmerkModel] = []
    datumBeginGeldigheid: str | None = None
    datumEindeGeldigheid: str | None = None
    bronBewaartermijn: str = ""
    selectiecategorie: str = ""
    archiefnominatie: str = ""
    toelichtingBewaartermijn: str = ""

    model_config = ConfigDict(from_attributes=True)


class PublicationListResponse(BaseModel):
    """Response model for list of publications."""

    count: int
    results: list[PublicationResponse]


def publication_to_response(pub: Publication) -> PublicationResponse:
    """Convert Publication model to response."""
    return PublicationResponse(
        uuid=str(pub.uuid),
        publisher=str(pub.publisher.uuid) if pub.publisher else "",
        verantwoordelijke=str(pub.verantwoordelijke.uuid) if pub.verantwoordelijke else "",
        officieleTitel=pub.officiele_titel,
        verkorteTitel=pub.verkorte_titel or "",
        omschrijving=pub.omschrijving or "",
        publicatiestatus=pub.publicatiestatus,
        informatieCategorieen=[str(cat.uuid) for cat in pub.informatie_categorieen],
        onderwerpen=[str(topic.uuid) for topic in pub.onderwerpen],
        eigenaar=EigenaarResponse(
            identifier=pub.eigenaar.identifier,
            weergaveNaam=pub.eigenaar.naam,
        ) if pub.eigenaar else None,
        eigenaarGroep=EigenaarGroepResponse(
            identifier=pub.eigenaar_groep.identifier,
            weergaveNaam=pub.eigenaar_groep.naam,
        ) if pub.eigenaar_groep else None,
        registratiedatum=pub.registratiedatum.isoformat() if pub.registratiedatum else "",
        laatstGewijzigdDatum=pub.laatst_gewijzigd_datum.isoformat() if pub.laatst_gewijzigd_datum else "",
        kenmerken=[
            KenmerkModel(kenmerk=ident.kenmerk, bron=ident.bron)
            for ident in pub.identifiers
        ],
        datumBeginGeldigheid=pub.datum_begin_geldigheid.isoformat() if pub.datum_begin_geldigheid else None,
        datumEindeGeldigheid=pub.datum_einde_geldigheid.isoformat() if pub.datum_einde_geldigheid else None,
        bronBewaartermijn=pub.bron_bewaartermijn or "",
        selectiecategorie=pub.selectiecategorie or "",
        archiefnominatie=pub.archiefnominatie or "",
        toelichtingBewaartermijn=pub.toelichting_bewaartermijn or "",
    )


async def get_or_create_member(db: AsyncSession, identifier: str) -> OrganisationMember:
    """Get or create an organisation member."""
    result = await db.execute(
        select(OrganisationMember).where(OrganisationMember.identifier == identifier)
    )
    member = result.scalar_one_or_none()

    if not member:
        member = OrganisationMember(identifier=identifier, naam=identifier)
        db.add(member)
        await db.flush()

    return member


async def get_or_create_unit(db: AsyncSession, identifier: str, naam: str) -> OrganisationUnit:
    """Get or create an organisation unit."""
    result = await db.execute(
        select(OrganisationUnit).where(OrganisationUnit.identifier == identifier)
    )
    unit = result.scalar_one_or_none()

    if not unit:
        unit = OrganisationUnit(identifier=identifier, naam=naam)
        db.add(unit)
        await db.flush()

    return unit


@router.get("/publicaties", response_model=PublicationListResponse)
async def list_publications(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="page_size"),
    sorteer: str = Query("-registratiedatum"),
    publicatiestatus: str | None = Query(None, alias="status"),
) -> PublicationListResponse:
    """List all publications with optional filters."""
    # Base query with eager loading
    query = select(Publication).options(
        selectinload(Publication.publisher),
        selectinload(Publication.verantwoordelijke),
        selectinload(Publication.eigenaar),
        selectinload(Publication.eigenaar_groep),
        selectinload(Publication.informatie_categorieen),
        selectinload(Publication.onderwerpen),
        selectinload(Publication.identifiers),
    )

    # Apply status filter
    if publicatiestatus:
        query = query.where(Publication.publicatiestatus == publicatiestatus)

    # Apply sorting
    if sorteer.startswith("-"):
        sort_field = sorteer[1:]
        descending = True
    else:
        sort_field = sorteer
        descending = False

    sort_column = getattr(Publication, sort_field, Publication.registratiedatum)
    query = query.order_by(sort_column.desc() if descending else sort_column.asc())

    # Get count
    count_query = select(func.count(Publication.id))
    if publicatiestatus:
        count_query = count_query.where(Publication.publicatiestatus == publicatiestatus)
    count_result = await db.execute(count_query)
    count = count_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    publications = result.scalars().all()

    return PublicationListResponse(
        count=count,
        results=[publication_to_response(pub) for pub in publications],
    )


@router.get("/publicaties/{pub_uuid}", response_model=PublicationResponse)
async def get_publication(
    pub_uuid: uuid_module.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicationResponse:
    """Get a single publication by UUID."""
    query = select(Publication).options(
        selectinload(Publication.publisher),
        selectinload(Publication.verantwoordelijke),
        selectinload(Publication.eigenaar),
        selectinload(Publication.eigenaar_groep),
        selectinload(Publication.informatie_categorieen),
        selectinload(Publication.onderwerpen),
        selectinload(Publication.identifiers),
    ).where(Publication.uuid == pub_uuid)

    result = await db.execute(query)
    pub = result.scalar_one_or_none()

    if not pub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found",
        )

    return publication_to_response(pub)


@router.post("/publicaties", response_model=PublicationResponse, status_code=status.HTTP_201_CREATED)
async def create_publication(
    db: Annotated[AsyncSession, Depends(get_db)],
    body: PublicationCreate = Body(...),
) -> PublicationResponse:
    """Create a new publication."""
    now = datetime.now(timezone.utc)

    # Look up publisher organisation
    publisher = None
    if body.publisher:
        result = await db.execute(
            select(Organisation).where(Organisation.uuid == uuid_module.UUID(body.publisher))
        )
        publisher = result.scalar_one_or_none()

    # Look up verantwoordelijke organisation
    verantwoordelijke = None
    if body.verantwoordelijke:
        result = await db.execute(
            select(Organisation).where(Organisation.uuid == uuid_module.UUID(body.verantwoordelijke))
        )
        verantwoordelijke = result.scalar_one_or_none()

    # Get or create eigenaar
    eigenaar = await get_or_create_member(db, "dev-user")

    # Get or create eigenaar_groep
    eigenaar_groep = None
    if body.eigenaarGroep and body.eigenaarGroep.get("identifier"):
        eigenaar_groep = await get_or_create_unit(
            db,
            body.eigenaarGroep["identifier"],
            body.eigenaarGroep.get("weergaveNaam", body.eigenaarGroep["identifier"]),
        )

    # Look up categories
    categories = []
    for cat_uuid_str in body.informatieCategorieen:
        result = await db.execute(
            select(InformationCategory).where(
                InformationCategory.uuid == uuid_module.UUID(cat_uuid_str)
            )
        )
        cat = result.scalar_one_or_none()
        if cat:
            categories.append(cat)

    # Look up topics
    topics = []
    for topic_uuid_str in body.onderwerpen:
        result = await db.execute(
            select(Topic).where(Topic.uuid == uuid_module.UUID(topic_uuid_str))
        )
        topic = result.scalar_one_or_none()
        if topic:
            topics.append(topic)

    # Parse date fields
    datum_begin = None
    if body.datumBeginGeldigheid:
        try:
            datum_begin = date.fromisoformat(body.datumBeginGeldigheid)
        except ValueError:
            pass

    datum_einde = None
    if body.datumEindeGeldigheid:
        try:
            datum_einde = date.fromisoformat(body.datumEindeGeldigheid)
        except ValueError:
            pass

    # Create publication
    pub = Publication(
        uuid=uuid_module.uuid4(),
        officiele_titel=body.officieleTitel,
        verkorte_titel=body.verkorteTitel,
        omschrijving=body.omschrijving,
        publicatiestatus=body.publicatiestatus or PublicationStatus.CONCEPT.value,
        publisher=publisher,
        verantwoordelijke=verantwoordelijke,
        eigenaar=eigenaar,
        eigenaar_groep=eigenaar_groep,
        registratiedatum=now,
        laatst_gewijzigd_datum=now,
        datum_begin_geldigheid=datum_begin,
        datum_einde_geldigheid=datum_einde,
        bron_bewaartermijn=body.bronBewaartermijn,
        selectiecategorie=body.selectiecategorie,
        archiefnominatie=body.archiefnominatie,
        toelichting_bewaartermijn=body.toelichtingBewaartermijn,
        informatie_categorieen=categories,
        onderwerpen=topics,
    )

    # Add identifiers (kenmerken)
    for kenmerk in body.kenmerken:
        pub.identifiers.append(
            PublicationIdentifier(kenmerk=kenmerk.kenmerk, bron=kenmerk.bron)
        )

    db.add(pub)
    await db.commit()
    await db.refresh(pub)

    return await get_publication(pub.uuid, db)


@router.put("/publicaties/{pub_uuid}", response_model=PublicationResponse)
async def update_publication(
    pub_uuid: uuid_module.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    body: PublicationCreate = Body(...),
) -> PublicationResponse:
    """Update a publication."""
    # Fetch existing publication
    query = select(Publication).options(
        selectinload(Publication.identifiers),
        selectinload(Publication.informatie_categorieen),
        selectinload(Publication.onderwerpen),
    ).where(Publication.uuid == pub_uuid)

    result = await db.execute(query)
    pub = result.scalar_one_or_none()

    if not pub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found",
        )

    now = datetime.now(timezone.utc)

    # Update basic fields
    pub.officiele_titel = body.officieleTitel
    pub.verkorte_titel = body.verkorteTitel
    pub.omschrijving = body.omschrijving
    pub.publicatiestatus = body.publicatiestatus
    pub.laatst_gewijzigd_datum = now
    pub.bron_bewaartermijn = body.bronBewaartermijn
    pub.selectiecategorie = body.selectiecategorie
    pub.archiefnominatie = body.archiefnominatie
    pub.toelichting_bewaartermijn = body.toelichtingBewaartermijn

    # Update publisher
    if body.publisher:
        result = await db.execute(
            select(Organisation).where(Organisation.uuid == uuid_module.UUID(body.publisher))
        )
        pub.publisher = result.scalar_one_or_none()
    else:
        pub.publisher = None

    # Update verantwoordelijke
    if body.verantwoordelijke:
        result = await db.execute(
            select(Organisation).where(Organisation.uuid == uuid_module.UUID(body.verantwoordelijke))
        )
        pub.verantwoordelijke = result.scalar_one_or_none()
    else:
        pub.verantwoordelijke = None

    # Update eigenaar_groep
    if body.eigenaarGroep and body.eigenaarGroep.get("identifier"):
        pub.eigenaar_groep = await get_or_create_unit(
            db,
            body.eigenaarGroep["identifier"],
            body.eigenaarGroep.get("weergaveNaam", body.eigenaarGroep["identifier"]),
        )
    else:
        pub.eigenaar_groep = None

    # Update date fields
    if body.datumBeginGeldigheid:
        try:
            pub.datum_begin_geldigheid = date.fromisoformat(body.datumBeginGeldigheid)
        except ValueError:
            pass
    else:
        pub.datum_begin_geldigheid = None

    if body.datumEindeGeldigheid:
        try:
            pub.datum_einde_geldigheid = date.fromisoformat(body.datumEindeGeldigheid)
        except ValueError:
            pass
    else:
        pub.datum_einde_geldigheid = None

    # Update categories
    pub.informatie_categorieen.clear()
    for cat_uuid_str in body.informatieCategorieen:
        result = await db.execute(
            select(InformationCategory).where(
                InformationCategory.uuid == uuid_module.UUID(cat_uuid_str)
            )
        )
        cat = result.scalar_one_or_none()
        if cat:
            pub.informatie_categorieen.append(cat)

    # Update topics
    pub.onderwerpen.clear()
    for topic_uuid_str in body.onderwerpen:
        result = await db.execute(
            select(Topic).where(Topic.uuid == uuid_module.UUID(topic_uuid_str))
        )
        topic = result.scalar_one_or_none()
        if topic:
            pub.onderwerpen.append(topic)

    # Update identifiers - must flush after clear to avoid unique constraint violation
    pub.identifiers.clear()
    await db.flush()  # Delete old identifiers before inserting new ones
    for kenmerk in body.kenmerken:
        pub.identifiers.append(
            PublicationIdentifier(kenmerk=kenmerk.kenmerk, bron=kenmerk.bron)
        )

    await db.commit()

    return await get_publication(pub_uuid, db)


@router.delete("/publicaties/{pub_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_publication(
    pub_uuid: uuid_module.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a publication."""
    result = await db.execute(
        select(Publication).where(Publication.uuid == pub_uuid)
    )
    pub = result.scalar_one_or_none()

    if not pub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found",
        )

    await db.delete(pub)
    await db.commit()


@router.post("/publicaties/{pub_uuid}/publish", response_model=PublicationResponse)
async def publish_publication(
    pub_uuid: uuid_module.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicationResponse:
    """Publish a publication (transition from concept to gepubliceerd)."""
    result = await db.execute(
        select(Publication).where(Publication.uuid == pub_uuid)
    )
    pub = result.scalar_one_or_none()

    if not pub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found",
        )

    if pub.publicatiestatus not in (PublicationStatus.CONCEPT.value, ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Publication can only be published from concept status",
        )

    now = datetime.now(timezone.utc)
    pub.publicatiestatus = PublicationStatus.GEPUBLICEERD.value
    pub.gepubliceerd_op = now
    pub.laatst_gewijzigd_datum = now

    await db.commit()

    return await get_publication(pub_uuid, db)


@router.post("/publicaties/{pub_uuid}/revoke", response_model=PublicationResponse)
async def revoke_publication(
    pub_uuid: uuid_module.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicationResponse:
    """Revoke a publication (transition from gepubliceerd to ingetrokken)."""
    result = await db.execute(
        select(Publication).where(Publication.uuid == pub_uuid)
    )
    pub = result.scalar_one_or_none()

    if not pub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication not found",
        )

    if pub.publicatiestatus != PublicationStatus.GEPUBLICEERD.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Publication can only be revoked from published status",
        )

    now = datetime.now(timezone.utc)
    pub.publicatiestatus = PublicationStatus.INGETROKKEN.value
    pub.ingetrokken_op = now
    pub.laatst_gewijzigd_datum = now

    await db.commit()

    return await get_publication(pub_uuid, db)
