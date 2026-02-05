"""Client for GPP-publicatiebank API.

Provides methods to retrieve documents from the publicatiebank by UUID.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx
import structlog

from woo_hoo.config import get_settings

if TYPE_CHECKING:
    from uuid import UUID

logger = structlog.get_logger(__name__)


class PublicatiebankError(Exception):
    """Base exception for publicatiebank errors."""


class PublicatiebankNotConfiguredError(PublicatiebankError):
    """Raised when publicatiebank is not configured."""


class DocumentNotFoundError(PublicatiebankError):
    """Raised when document is not found in publicatiebank."""


class DocumentDownloadError(PublicatiebankError):
    """Raised when document download fails."""


@dataclass
class PublicatiebankDocument:
    """Document retrieved from publicatiebank."""

    uuid: str
    officiele_titel: str
    verkorte_titel: str | None
    omschrijving: str | None
    bestandsnaam: str
    bestandsformaat: str
    bestandsomvang: int
    publicatiestatus: str
    content: bytes
    kenmerken: list[dict[str, str]]


class PublicatiebankClient:
    """Client for interacting with GPP-publicatiebank API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        timeout: float = 60.0,
    ):
        """Initialize the publicatiebank client.

        Args:
            base_url: Base URL of the publicatiebank API. Defaults to settings.
            api_token: API token for authentication. Defaults to settings.
            timeout: Request timeout in seconds.
        """
        settings = get_settings()
        self.base_url = (base_url or settings.gpp_publicatiebank_url or "").rstrip("/")
        self.api_token = api_token or settings.gpp_api_token
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        """Check if publicatiebank is configured."""
        return bool(self.base_url)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Accept": "application/json",
            }
            if self.api_token:
                headers["Authorization"] = f"Token {self.api_token}"

            # ODRC requires audit headers for request tracking
            headers["Audit-User-ID"] = "woo-hoo-service"
            headers["Audit-User-Representation"] = "Woo-Hoo Metadata Generation Service"
            headers["Audit-Remarks"] = "Automated metadata generation"

            # Use explicit timeout configuration for large file downloads
            # Read timeout needs to be higher for streaming large PDFs
            timeout_config = httpx.Timeout(
                connect=30.0,  # Time to establish connection
                read=300.0,    # Time to read response data (5 minutes for large files)
                write=30.0,    # Time to write request data
                pool=30.0,     # Time to acquire connection from pool
            )
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=timeout_config,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_document_metadata(self, document_uuid: str | UUID) -> dict:
        """Get document metadata from publicatiebank.

        Args:
            document_uuid: UUID of the document.

        Returns:
            Document metadata as dict.

        Raises:
            PublicatiebankNotConfiguredError: If publicatiebank is not configured.
            DocumentNotFoundError: If document is not found.
            PublicatiebankError: For other API errors.
        """
        if not self.is_configured:
            raise PublicatiebankNotConfiguredError("GPP_PUBLICATIEBANK_URL is not configured")

        client = await self._get_client()
        url = f"/api/v2/documenten/{document_uuid}"

        logger.info("Fetching document metadata", uuid=str(document_uuid), url=url)

        try:
            response = await client.get(url)

            if response.status_code == 404:
                raise DocumentNotFoundError(f"Document {document_uuid} not found in publicatiebank")

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error("Publicatiebank API error", status_code=e.response.status_code, detail=e.response.text)
            raise PublicatiebankError(f"Publicatiebank API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error("Publicatiebank request failed", error=str(e))
            raise PublicatiebankError(f"Failed to connect to publicatiebank: {e}") from e

    async def download_document(self, document_uuid: str | UUID) -> bytes:
        """Download document content from publicatiebank.

        Args:
            document_uuid: UUID of the document.

        Returns:
            Document content as bytes.

        Raises:
            PublicatiebankNotConfiguredError: If publicatiebank is not configured.
            DocumentNotFoundError: If document is not found.
            DocumentDownloadError: If download fails.
        """
        if not self.is_configured:
            raise PublicatiebankNotConfiguredError("GPP_PUBLICATIEBANK_URL is not configured")

        client = await self._get_client()
        url = f"/api/v2/documenten/{document_uuid}/download"

        logger.info("Downloading document", uuid=str(document_uuid), url=url)

        try:
            response = await client.get(url)

            if response.status_code == 404:
                raise DocumentNotFoundError(f"Document {document_uuid} not found in publicatiebank")

            if response.status_code == 409:
                raise DocumentDownloadError(f"Document {document_uuid} upload is not yet completed")

            response.raise_for_status()
            return response.content

        except httpx.HTTPStatusError as e:
            logger.error("Document download failed", status_code=e.response.status_code, detail=e.response.text)
            raise DocumentDownloadError(f"Download failed: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error("Download request failed", error=str(e))
            raise DocumentDownloadError(f"Failed to download document: {e}") from e

    async def get_document(self, document_uuid: str | UUID) -> PublicatiebankDocument:
        """Get document with metadata and content from publicatiebank.

        Args:
            document_uuid: UUID of the document.

        Returns:
            PublicatiebankDocument with metadata and content.

        Raises:
            PublicatiebankNotConfiguredError: If publicatiebank is not configured.
            DocumentNotFoundError: If document is not found.
            DocumentDownloadError: If download fails.
        """
        # Fetch metadata and content
        metadata = await self.get_document_metadata(document_uuid)
        content = await self.download_document(document_uuid)

        logger.info(
            "Document retrieved",
            uuid=str(document_uuid),
            title=metadata.get("officiele_titel"),
            size=len(content),
        )

        return PublicatiebankDocument(
            uuid=metadata["uuid"],
            officiele_titel=metadata["officiele_titel"],
            verkorte_titel=metadata.get("verkorte_titel"),
            omschrijving=metadata.get("omschrijving"),
            bestandsnaam=metadata["bestandsnaam"],
            bestandsformaat=metadata["bestandsformaat"],
            bestandsomvang=metadata["bestandsomvang"],
            publicatiestatus=metadata["publicatiestatus"],
            content=content,
            kenmerken=metadata.get("kenmerken", []),
        )
