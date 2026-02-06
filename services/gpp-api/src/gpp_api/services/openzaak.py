"""OpenZaak client for Documents API integration."""

from __future__ import annotations

import base64
import hashlib
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx
from authlib.jose import jwt

from gpp_api.config import get_settings
from gpp_api.utils.logging import get_logger

if TYPE_CHECKING:
    from gpp_api.db.models.metadata import InformationCategory

logger = get_logger(__name__)


def create_zgw_jwt(client_id: str, secret: str, user_id: str = "gpp-api") -> str:
    """Create a ZGW JWT token for OpenZaak authentication.

    This follows the ZGW (Zaakgericht Werken) JWT specification used by zgw-consumers.

    Args:
        client_id: API client ID
        secret: API secret
        user_id: User identifier for audit trail

    Returns:
        JWT token string
    """
    now = int(time.time())

    header = {
        "typ": "JWT",
        "alg": "HS256",
        "client_identifier": client_id,
    }

    payload = {
        "iss": client_id,
        "iat": now,
        "client_id": client_id,
        "user_id": user_id,
        "user_representation": user_id,
    }

    return jwt.encode(header, payload, secret).decode("utf-8")


@dataclass
class OpenZaakDocument:
    """Response from OpenZaak document creation."""

    url: str
    uuid: uuid.UUID
    identificatie: str
    bronorganisatie: str
    creatiedatum: str
    titel: str
    vertrouwelijkheidaanduiding: str
    auteur: str
    status: str
    formaat: str
    taal: str
    bestandsnaam: str
    bestandsomvang: int | None
    link: str
    beschrijving: str
    informatieobjecttype: str
    locked: bool
    lock: str


class OpenZaakError(Exception):
    """Base exception for OpenZaak errors."""


class OpenZaakAuthError(OpenZaakError):
    """Authentication error."""


class OpenZaakValidationError(OpenZaakError):
    """Validation error from OpenZaak."""


class OpenZaakClient:
    """Client for OpenZaak Documents API."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        settings: Any | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._external_client = client
        self._internal_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._external_client:
            return self._external_client

        if self._internal_client is None:
            self._internal_client = httpx.AsyncClient(
                base_url=self._settings.openzaak_documents_api_url,
                timeout=60.0,
            )
        return self._internal_client

    async def close(self) -> None:
        """Close the internal HTTP client."""
        if self._internal_client:
            await self._internal_client.aclose()
            self._internal_client = None

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for OpenZaak.

        Uses ZGW JWT authentication following zgw-consumers pattern.
        """
        token = create_zgw_jwt(
            client_id=self._settings.openzaak_client_id,
            secret=self._settings.openzaak_secret,
            user_id="gpp-api",
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        return headers

    def get_informatieobjecttype_url(
        self,
        category: InformationCategory,
    ) -> str:
        """Construct the informatieobjecttype URL for OpenZaak's Catalogi API.

        CRITICAL: The URL must point to OpenZaak's Catalogi API, not publicatiebank's.
        This is the key fix from the 001_fix_informatieobjecttype_url.py patch.

        Args:
            category: The information category (with UUID matching OpenZaak's InformatieObjectType)

        Returns:
            Full URL to the informatieobjecttype in OpenZaak's Catalogi API
        """
        base_url = self._settings.openzaak_catalogi_api_url.rstrip("/")
        return f"{base_url}/informatieobjecttypen/{category.uuid}"

    async def create_document(
        self,
        titel: str,
        informatieobjecttype_url: str,
        bronorganisatie: str,
        creatiedatum: str,
        bestandsnaam: str | None = None,
        bestandsomvang: int | None = None,
        formaat: str | None = None,
        auteur: str = "GPP",
        beschrijving: str = "",
        taal: str = "nld",
        vertrouwelijkheidaanduiding: str = "openbaar",
        status: str = "definitief",
    ) -> OpenZaakDocument:
        """Create a document in OpenZaak Documents API.

        Args:
            titel: Document title
            informatieobjecttype_url: URL to the informatieobjecttype in Catalogi API
            bronorganisatie: RSIN of the source organisation
            creatiedatum: Creation date (YYYY-MM-DD)
            bestandsnaam: Filename
            bestandsomvang: File size in bytes
            formaat: MIME type
            auteur: Author name
            beschrijving: Description
            taal: Language code (ISO 639-2/T)
            vertrouwelijkheidaanduiding: Confidentiality level
            status: Document status

        Returns:
            Created document info

        Raises:
            OpenZaakValidationError: If validation fails
            OpenZaakError: For other errors
        """
        client = await self._get_client()

        payload = {
            "bronorganisatie": bronorganisatie,
            "creatiedatum": creatiedatum,
            "titel": titel,
            "auteur": auteur,
            "taal": taal,
            "informatieobjecttype": informatieobjecttype_url,
            "vertrouwelijkheidaanduiding": vertrouwelijkheidaanduiding,
            "status": status,
        }

        if bestandsnaam:
            payload["bestandsnaam"] = bestandsnaam
        if bestandsomvang is not None:
            payload["bestandsomvang"] = bestandsomvang
        if formaat:
            payload["formaat"] = formaat
        if beschrijving:
            payload["beschrijving"] = beschrijving

        logger.info(
            "openzaak_create_document",
            titel=titel,
            informatieobjecttype=informatieobjecttype_url,
        )

        response = await client.post(
            "/enkelvoudiginformatieobjecten",
            json=payload,
            headers=self._get_auth_headers(),
        )

        if response.status_code == 400:
            error_data = response.json()
            logger.error(
                "openzaak_validation_error",
                status=response.status_code,
                error=error_data,
            )
            raise OpenZaakValidationError(f"Validation failed: {error_data}")

        if response.status_code == 401:
            raise OpenZaakAuthError("Authentication failed")

        response.raise_for_status()

        data = response.json()
        return OpenZaakDocument(
            url=data["url"],
            uuid=uuid.UUID(data["uuid"]),
            identificatie=data["identificatie"],
            bronorganisatie=data["bronorganisatie"],
            creatiedatum=data["creatiedatum"],
            titel=data["titel"],
            vertrouwelijkheidaanduiding=data["vertrouwelijkheidaanduiding"],
            auteur=data["auteur"],
            status=data["status"],
            formaat=data.get("formaat", ""),
            taal=data["taal"],
            bestandsnaam=data.get("bestandsnaam", ""),
            bestandsomvang=data.get("bestandsomvang"),
            link=data.get("link", ""),
            beschrijving=data.get("beschrijving", ""),
            informatieobjecttype=data["informatieobjecttype"],
            locked=data.get("locked", False),
            lock=data.get("lock", ""),
        )

    async def lock_document(self, document_url: str) -> str:
        """Lock a document for editing.

        Args:
            document_url: URL of the document to lock

        Returns:
            Lock value

        Raises:
            OpenZaakError: If locking fails
        """
        client = await self._get_client()

        response = await client.post(
            f"{document_url}/lock",
            headers=self._get_auth_headers(),
        )

        response.raise_for_status()

        data = response.json()
        lock = data.get("lock", "")
        logger.info("openzaak_document_locked", document_url=document_url)
        return lock

    async def unlock_document(self, document_url: str, lock: str) -> None:
        """Unlock a document.

        Args:
            document_url: URL of the document to unlock
            lock: Lock value from previous lock operation

        Raises:
            OpenZaakError: If unlocking fails
        """
        client = await self._get_client()

        response = await client.post(
            f"{document_url}/unlock",
            json={"lock": lock},
            headers=self._get_auth_headers(),
        )

        response.raise_for_status()
        logger.info("openzaak_document_unlocked", document_url=document_url)

    async def upload_file_part(
        self,
        document_url: str,
        lock: str,
        content: bytes,
        part_number: int = 1,
        is_final: bool = True,
    ) -> None:
        """Upload a file part to a document.

        Args:
            document_url: URL of the document
            lock: Lock value
            content: File content bytes
            part_number: Part number (for chunked uploads)
            is_final: Whether this is the final part

        Raises:
            OpenZaakError: If upload fails
        """
        client = await self._get_client()

        # Calculate checksum
        checksum = hashlib.md5(content).hexdigest()

        # Encode content as base64
        content_b64 = base64.b64encode(content).decode("utf-8")

        payload = {
            "lock": lock,
            "inhoud": content_b64,
            "bestandsomvang": len(content),
        }

        response = await client.patch(
            document_url,
            json=payload,
            headers=self._get_auth_headers(),
        )

        response.raise_for_status()
        logger.info(
            "openzaak_file_part_uploaded",
            document_url=document_url,
            part_number=part_number,
            size=len(content),
            checksum=checksum,
        )

    async def destroy_document(self, document_url: str) -> None:
        """Delete a document from OpenZaak.

        Args:
            document_url: URL of the document to delete

        Raises:
            OpenZaakError: If deletion fails
        """
        client = await self._get_client()

        response = await client.delete(
            document_url,
            headers=self._get_auth_headers(),
        )

        response.raise_for_status()
        logger.info("openzaak_document_destroyed", document_url=document_url)

    async def get_document(self, document_url: str) -> dict[str, Any]:
        """Get document details from OpenZaak.

        Args:
            document_url: URL of the document

        Returns:
            Document data

        Raises:
            OpenZaakError: If retrieval fails
        """
        client = await self._get_client()

        response = await client.get(
            document_url,
            headers=self._get_auth_headers(),
        )

        response.raise_for_status()
        return response.json()

    async def download_document_content(self, document_url: str) -> bytes:
        """Download document file content from OpenZaak.

        Args:
            document_url: URL of the document

        Returns:
            File content as bytes

        Raises:
            OpenZaakError: If download fails
        """
        client = await self._get_client()

        # Use auth headers but with Accept for binary content
        token = create_zgw_jwt(
            client_id=self._settings.openzaak_client_id,
            secret=self._settings.openzaak_secret,
            user_id="gpp-api",
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "*/*",  # Accept any content type for download
        }

        # Get the download URL
        response = await client.get(
            f"{document_url}/download",
            headers=headers,
            follow_redirects=True,
        )

        response.raise_for_status()
        return response.content


# Singleton instance getter
_client: OpenZaakClient | None = None


def get_openzaak_client() -> OpenZaakClient:
    """Get the singleton OpenZaak client.

    Returns:
        OpenZaakClient instance
    """
    global _client
    if _client is None:
        _client = OpenZaakClient()
    return _client
