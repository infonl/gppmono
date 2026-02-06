"""Document endpoints using SQLAlchemy models."""

from __future__ import annotations

import uuid as uuid_module
from datetime import datetime, date, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from gpp_api.api.deps import get_db
from gpp_api.services.openzaak import OpenZaakClient, OpenZaakError
from gpp_api.db.models import (
    Document,
    DocumentIdentifier,
    Publication,
    PublicationStatus,
    OrganisationMember,
)

router = APIRouter()


# Pydantic models for request/response
class EigenaarResponse(BaseModel):
    """Owner response model."""

    identifier: str
    weergaveNaam: str

    class Config:
        from_attributes = True


class KenmerkModel(BaseModel):
    """Identifier model."""

    kenmerk: str
    bron: str

    class Config:
        from_attributes = True


class BestandsdeelResponse(BaseModel):
    """File part response model."""

    url: str
    volgnummer: int
    omvang: int


class DocumentCreate(BaseModel):
    """Request model for creating a document."""

    publicatie: str
    officieleTitel: str
    verkorteTitel: str = ""
    omschrijving: str = ""
    creatiedatum: str
    bestandsnaam: str
    bestandsformaat: str
    bestandsomvang: int
    publicatiestatus: str = "concept"
    kenmerken: list[KenmerkModel] = []
    ontvangstdatum: str | None = None
    datumOndertekend: str | None = None


class DocumentResponse(BaseModel):
    """Response model for a document."""

    uuid: str
    publicatie: str
    officieleTitel: str
    verkorteTitel: str
    omschrijving: str
    creatiedatum: str
    bestandsnaam: str
    bestandsformaat: str
    bestandsomvang: int
    publicatiestatus: str
    eigenaar: EigenaarResponse | None = None
    registratiedatum: str
    laatstGewijzigdDatum: str
    kenmerken: list[KenmerkModel] = []
    bestandsdelen: list[BestandsdeelResponse] | None = None
    ontvangstdatum: str | None = None
    datumOndertekend: str | None = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response model for list of documents."""

    count: int
    results: list[DocumentResponse]


def document_to_response(doc: Document) -> DocumentResponse:
    """Convert Document model to response."""
    return DocumentResponse(
        uuid=str(doc.uuid),
        publicatie=str(doc.publicatie.uuid) if doc.publicatie else "",
        officieleTitel=doc.officiele_titel,
        verkorteTitel=doc.verkorte_titel or "",
        omschrijving=doc.omschrijving or "",
        creatiedatum=doc.creatiedatum.isoformat() if doc.creatiedatum else "",
        bestandsnaam=doc.bestandsnaam or "",
        bestandsformaat=doc.bestandsformaat or "",
        bestandsomvang=doc.bestandsomvang or 0,
        publicatiestatus=doc.publicatiestatus,
        eigenaar=EigenaarResponse(
            identifier=doc.eigenaar.identifier,
            weergaveNaam=doc.eigenaar.naam,
        ) if doc.eigenaar else None,
        registratiedatum=doc.registratiedatum.isoformat() if doc.registratiedatum else "",
        laatstGewijzigdDatum=doc.laatst_gewijzigd_datum.isoformat() if doc.laatst_gewijzigd_datum else "",
        kenmerken=[
            KenmerkModel(kenmerk=ident.kenmerk, bron=ident.bron)
            for ident in doc.identifiers
        ],
        bestandsdelen=None,  # TODO: Implement file parts via OpenZaak
        ontvangstdatum=doc.ontvangstdatum.isoformat() if doc.ontvangstdatum else None,
        datumOndertekend=doc.datum_ondertekend.isoformat() if doc.datum_ondertekend else None,
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


@router.get("/documenten", response_model=DocumentListResponse)
async def list_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    publicatie: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> DocumentListResponse:
    """List all documents with optional filters."""
    # Base query with eager loading
    query = select(Document).options(
        selectinload(Document.publicatie),
        selectinload(Document.eigenaar),
        selectinload(Document.identifiers),
    )

    # Filter by publication UUID
    if publicatie:
        try:
            pub_uuid = uuid_module.UUID(publicatie)
            # Join with Publication to filter by UUID
            query = query.join(Publication).where(Publication.uuid == pub_uuid)
        except ValueError:
            return DocumentListResponse(count=0, results=[])

    # Order by registratiedatum
    query = query.order_by(Document.registratiedatum.desc())

    # Get count
    count_query = select(func.count(Document.id))
    if publicatie:
        try:
            pub_uuid = uuid_module.UUID(publicatie)
            count_query = count_query.join(Publication).where(Publication.uuid == pub_uuid)
        except ValueError:
            pass
    count_result = await db.execute(count_query)
    count = count_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    documents = result.scalars().all()

    return DocumentListResponse(
        count=count,
        results=[document_to_response(doc) for doc in documents],
    )


@router.get("/documenten/{doc_uuid}", response_model=DocumentResponse)
async def get_document(
    doc_uuid: uuid_module.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentResponse:
    """Get a single document by UUID."""
    query = select(Document).options(
        selectinload(Document.publicatie),
        selectinload(Document.eigenaar),
        selectinload(Document.identifiers),
    ).where(Document.uuid == doc_uuid)

    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document_to_response(doc)


@router.post("/documenten", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    db: Annotated[AsyncSession, Depends(get_db)],
    body: DocumentCreate = Body(...),
) -> DocumentResponse:
    """Create a new document."""
    now = datetime.now(timezone.utc)

    # Look up publication
    try:
        pub_uuid = uuid_module.UUID(body.publicatie)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid publication UUID",
        )

    result = await db.execute(
        select(Publication).where(Publication.uuid == pub_uuid)
    )
    publication = result.scalar_one_or_none()

    if not publication:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Publication not found",
        )

    # Get or create eigenaar
    eigenaar = await get_or_create_member(db, "dev-user")

    # Parse creatiedatum
    try:
        creatiedatum = date.fromisoformat(body.creatiedatum.replace("Z", "+00:00").split("T")[0])
    except ValueError:
        creatiedatum = date.today()

    # Parse optional dates
    ontvangstdatum = None
    if body.ontvangstdatum:
        try:
            ontvangstdatum = datetime.fromisoformat(body.ontvangstdatum.replace("Z", "+00:00"))
        except ValueError:
            pass

    datum_ondertekend = None
    if body.datumOndertekend:
        try:
            datum_ondertekend = datetime.fromisoformat(body.datumOndertekend.replace("Z", "+00:00"))
        except ValueError:
            pass

    # Create document
    doc = Document(
        uuid=uuid_module.uuid4(),
        publicatie=publication,
        eigenaar=eigenaar,
        officiele_titel=body.officieleTitel,
        verkorte_titel=body.verkorteTitel,
        omschrijving=body.omschrijving,
        creatiedatum=creatiedatum,
        bestandsnaam=body.bestandsnaam,
        bestandsformaat=body.bestandsformaat,
        bestandsomvang=body.bestandsomvang,
        publicatiestatus=body.publicatiestatus or PublicationStatus.CONCEPT.value,
        registratiedatum=now,
        laatst_gewijzigd_datum=now,
        ontvangstdatum=ontvangstdatum,
        datum_ondertekend=datum_ondertekend,
    )

    # Add identifiers (kenmerken)
    for kenmerk in body.kenmerken:
        doc.identifiers.append(
            DocumentIdentifier(kenmerk=kenmerk.kenmerk, bron=kenmerk.bron)
        )

    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return await get_document(doc.uuid, db)


@router.put("/documenten/{doc_uuid}", response_model=DocumentResponse)
async def update_document(
    doc_uuid: uuid_module.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    body: DocumentCreate = Body(...),
) -> DocumentResponse:
    """Update a document."""
    # Fetch existing document
    query = select(Document).options(
        selectinload(Document.identifiers),
    ).where(Document.uuid == doc_uuid)

    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    now = datetime.now(timezone.utc)

    # Update fields
    doc.officiele_titel = body.officieleTitel
    doc.verkorte_titel = body.verkorteTitel
    doc.omschrijving = body.omschrijving
    doc.bestandsnaam = body.bestandsnaam
    doc.bestandsformaat = body.bestandsformaat
    doc.bestandsomvang = body.bestandsomvang
    doc.publicatiestatus = body.publicatiestatus
    doc.laatst_gewijzigd_datum = now

    # Parse creatiedatum
    if body.creatiedatum:
        try:
            doc.creatiedatum = date.fromisoformat(body.creatiedatum.replace("Z", "+00:00").split("T")[0])
        except ValueError:
            pass

    # Parse optional dates
    if body.ontvangstdatum:
        try:
            doc.ontvangstdatum = datetime.fromisoformat(body.ontvangstdatum.replace("Z", "+00:00"))
        except ValueError:
            pass
    else:
        doc.ontvangstdatum = None

    if body.datumOndertekend:
        try:
            doc.datum_ondertekend = datetime.fromisoformat(body.datumOndertekend.replace("Z", "+00:00"))
        except ValueError:
            pass
    else:
        doc.datum_ondertekend = None

    # Update identifiers
    doc.identifiers.clear()
    for kenmerk in body.kenmerken:
        doc.identifiers.append(
            DocumentIdentifier(kenmerk=kenmerk.kenmerk, bron=kenmerk.bron)
        )

    await db.commit()

    return await get_document(doc_uuid, db)


@router.delete("/documenten/{doc_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_uuid: uuid_module.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a document."""
    result = await db.execute(
        select(Document).where(Document.uuid == doc_uuid)
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    await db.delete(doc)
    await db.commit()


@router.post("/documenten/{doc_uuid}/upload")
async def upload_document_file(
    doc_uuid: uuid_module.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Upload file content for a document.

    TODO: Implement file upload via OpenZaak Documents API.
    """
    result = await db.execute(
        select(Document).where(Document.uuid == doc_uuid)
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return {"uuid": str(doc_uuid), "status": "not_implemented"}


@router.get("/documenten/{doc_uuid}/download")
async def download_document_file(
    doc_uuid: uuid_module.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Download file content for a document from OpenZaak.

    Fetches the document from OpenZaak Documents API using the stored reference.
    """
    result = await db.execute(
        select(Document).where(Document.uuid == doc_uuid)
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if not doc.document_uuid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document not yet uploaded to OpenZaak",
        )

    openzaak_client = OpenZaakClient()
    document_url = f"/enkelvoudiginformatieobjecten/{doc.document_uuid}"

    try:
        content = await openzaak_client.download_document_content(document_url)

        # Determine content type from bestandsformaat or default
        content_type = "application/octet-stream"
        if doc.bestandsformaat:
            # bestandsformaat might be a MIME type or UUID reference
            if "/" in doc.bestandsformaat:
                content_type = doc.bestandsformaat
            elif doc.bestandsnaam and doc.bestandsnaam.endswith(".pdf"):
                content_type = "application/pdf"

        return StreamingResponse(
            iter([content]),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{doc.bestandsnaam}"',
            },
        )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found in OpenZaak",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenZaak error: {e.response.status_code}",
        )
    except (httpx.RequestError, OpenZaakError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to OpenZaak: {e}",
        )
    finally:
        await openzaak_client.close()
