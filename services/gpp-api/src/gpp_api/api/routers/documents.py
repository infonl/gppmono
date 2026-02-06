"""Document endpoints using SQLAlchemy models."""

from __future__ import annotations

import math
import uuid as uuid_module
from datetime import datetime, date, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from gpp_api.api.deps import get_db
from gpp_api.config import get_settings
from gpp_api.services.openzaak import OpenZaakClient, OpenZaakError, OpenZaakValidationError
from gpp_api.db.models import (
    Document,
    DocumentIdentifier,
    Publication,
    PublicationStatus,
    OrganisationMember,
    InformationCategory,
)
from gpp_api.utils.logging import get_logger

logger = get_logger(__name__)

# Chunk size for file uploads (10MB)
FILE_PART_SIZE = 10 * 1024 * 1024

router = APIRouter()


# Pydantic models for request/response
class EigenaarResponse(BaseModel):
    """Owner response model."""

    identifier: str
    weergaveNaam: str

    model_config = ConfigDict(from_attributes=True)


class KenmerkModel(BaseModel):
    """Identifier model."""

    kenmerk: str
    bron: str

    model_config = ConfigDict(from_attributes=True)


class BestandsdeelResponse(BaseModel):
    """File part response model."""

    url: str
    volgnummer: int
    omvang: int


def generate_bestandsdelen(doc_uuid: str, file_size: int) -> list[BestandsdeelResponse]:
    """Generate bestandsdelen (file part) upload URLs for a document.

    Args:
        doc_uuid: Document UUID
        file_size: Total file size in bytes

    Returns:
        List of BestandsdeelResponse with upload URLs
    """
    if file_size <= 0:
        return []

    settings = get_settings()
    base_url = settings.app_url.rstrip("/")
    num_parts = math.ceil(file_size / FILE_PART_SIZE)
    parts = []

    for i in range(num_parts):
        part_uuid = str(uuid_module.uuid4())
        start_offset = i * FILE_PART_SIZE
        part_size = min(FILE_PART_SIZE, file_size - start_offset)

        parts.append(
            BestandsdeelResponse(
                url=f"{base_url}/api/v2/documenten/{doc_uuid}/bestandsdelen/{part_uuid}",
                volgnummer=i + 1,
                omvang=part_size,
            )
        )

    return parts


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

    model_config = ConfigDict(from_attributes=True)


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
    """Create a new document.

    This creates the document metadata in the database and registers it with OpenZaak.
    Returns bestandsdelen array with upload URLs for the actual file content.
    """
    now = datetime.now(timezone.utc)
    settings = get_settings()

    # Look up publication with information categories
    try:
        pub_uuid = uuid_module.UUID(body.publicatie)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid publication UUID",
        )

    result = await db.execute(
        select(Publication)
        .options(selectinload(Publication.informatie_categorieen))
        .where(Publication.uuid == pub_uuid)
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

    # Generate document UUID
    doc_uuid = uuid_module.uuid4()

    # Register with OpenZaak Documents API
    openzaak_uuid = None
    openzaak_lock = ""

    if settings.openzaak_client_id and settings.openzaak_secret:
        # Get information category for informatieobjecttype
        category = publication.informatie_categorieen[0] if publication.informatie_categorieen else None

        if category:
            openzaak_client = OpenZaakClient()
            try:
                # Construct informatieobjecttype URL
                informatieobjecttype_url = openzaak_client.get_informatieobjecttype_url(category)

                # Get organisation RSIN - use default if not available
                bronorganisatie = "000000000"  # Default RSIN
                if publication.publisher and publication.publisher.rsin:
                    bronorganisatie = publication.publisher.rsin

                # Create document in OpenZaak
                # Note: OpenZaak returns the document already locked when bestandsomvang > 0
                oz_doc = await openzaak_client.create_document(
                    titel=body.officieleTitel,
                    informatieobjecttype_url=informatieobjecttype_url,
                    bronorganisatie=bronorganisatie,
                    creatiedatum=creatiedatum.isoformat(),
                    bestandsnaam=body.bestandsnaam,
                    bestandsomvang=body.bestandsomvang,
                    formaat=body.bestandsformaat,
                    auteur="GPP",
                    beschrijving=body.omschrijving,
                    status="in_bewerking",  # Start with in_bewerking for upload
                )

                openzaak_uuid = str(oz_doc.uuid)
                # Use the lock from the response - document is created pre-locked
                openzaak_lock = oz_doc.lock

                logger.info(
                    "openzaak_document_created",
                    doc_uuid=str(doc_uuid),
                    openzaak_uuid=openzaak_uuid,
                    lock=openzaak_lock,
                )

            except OpenZaakValidationError as e:
                logger.error("openzaak_validation_error", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"OpenZaak validation error: {e}",
                )
            except OpenZaakError as e:
                logger.error("openzaak_error", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"OpenZaak error: {e}",
                )
            finally:
                await openzaak_client.close()

    # Create document in database
    doc = Document(
        uuid=doc_uuid,
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
        # OpenZaak integration
        document_uuid=openzaak_uuid,
        lock=openzaak_lock,
        upload_complete=False,
        document_service_id=1 if openzaak_uuid else None,  # Placeholder service ID
    )

    # Add identifiers (kenmerken)
    for kenmerk in body.kenmerken:
        doc.identifiers.append(
            DocumentIdentifier(kenmerk=kenmerk.kenmerk, bron=kenmerk.bron)
        )

    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Generate bestandsdelen URLs for file upload
    bestandsdelen = generate_bestandsdelen(str(doc.uuid), body.bestandsomvang)

    # Return document with bestandsdelen
    response = document_to_response(doc)
    response.bestandsdelen = bestandsdelen

    return response


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

    # Update identifiers - must flush after clear to avoid unique constraint violation
    doc.identifiers.clear()
    await db.flush()  # Delete old identifiers before inserting new ones
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


@router.put("/documenten/{doc_uuid}/bestandsdelen/{part_uuid}")
async def upload_file_part(
    doc_uuid: uuid_module.UUID,
    part_uuid: uuid_module.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    inhoud: UploadFile = File(...),
) -> dict:
    """Upload a file part for a document.

    This receives multipart form data and uploads the file content to OpenZaak.
    Once all parts are uploaded, the document is unlocked in OpenZaak.

    Args:
        doc_uuid: Document UUID
        part_uuid: File part UUID (used for tracking)
        inhoud: The file content to upload

    Returns:
        Document status information
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document not registered with OpenZaak",
        )

    if not doc.lock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document not locked for upload",
        )

    # Read file content
    content = await inhoud.read()

    logger.info(
        "upload_file_part",
        doc_uuid=str(doc_uuid),
        part_uuid=str(part_uuid),
        size=len(content),
    )

    # Upload to OpenZaak
    openzaak_client = OpenZaakClient()
    try:
        settings = get_settings()
        document_url = f"{settings.openzaak_documents_api_url}/enkelvoudiginformatieobjecten/{doc.document_uuid}"

        await openzaak_client.upload_file_part(
            document_url=document_url,
            lock=doc.lock,
            content=content,
        )

        # Mark upload as complete and unlock
        await openzaak_client.unlock_document(document_url, doc.lock)

        # Update document status
        doc.upload_complete = True
        doc.lock = ""
        doc.metadata_gestript_op = datetime.now(timezone.utc)
        await db.commit()

        logger.info("upload_complete", doc_uuid=str(doc_uuid))

        return {"uuid": str(doc_uuid), "status": "completed", "uploadComplete": True}

    except OpenZaakError as e:
        logger.error("upload_error", doc_uuid=str(doc_uuid), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenZaak upload error: {e}",
        )
    finally:
        await openzaak_client.close()


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
