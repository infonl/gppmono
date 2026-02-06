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


class PublicationNotFoundError(PublicatiebankError):
    """Raised when publication is not found in publicatiebank."""


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


@dataclass
class PublicatiebankPublication:
    """Publication retrieved from publicatiebank."""

    uuid: str
    officiele_titel: str
    verkorte_titel: str | None
    omschrijving: str | None
    publicatiestatus: str
    publisher: str | None
    informatie_categorieen: list[str]
    onderwerpen: list[str]
    kenmerken: list[dict[str, str]]
    documents: list[PublicatiebankDocument]


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
                read=300.0,  # Time to read response data (5 minutes for large files)
                write=30.0,  # Time to write request data
                pool=30.0,  # Time to acquire connection from pool
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

        # Support both snake_case (publicatiebank) and camelCase (gpp-api) field names
        def get_field(data: dict, snake_case: str, camel_case: str, default=None):
            return data.get(snake_case) or data.get(camel_case) or default

        return PublicatiebankDocument(
            uuid=metadata["uuid"],
            officiele_titel=get_field(metadata, "officiele_titel", "officieleTitel"),
            verkorte_titel=get_field(metadata, "verkorte_titel", "verkorteTitel"),
            omschrijving=get_field(metadata, "omschrijving", "omschrijving"),
            bestandsnaam=get_field(metadata, "bestandsnaam", "bestandsnaam"),
            bestandsformaat=get_field(metadata, "bestandsformaat", "bestandsformaat"),
            bestandsomvang=get_field(metadata, "bestandsomvang", "bestandsomvang"),
            publicatiestatus=get_field(metadata, "publicatiestatus", "publicatiestatus"),
            content=content,
            kenmerken=get_field(metadata, "kenmerken", "kenmerken", []),
        )

    async def get_publication_metadata(self, publication_uuid: str | UUID) -> dict:
        """Get publication metadata from publicatiebank.

        Args:
            publication_uuid: UUID of the publication.

        Returns:
            Publication metadata as dict.

        Raises:
            PublicatiebankNotConfiguredError: If publicatiebank is not configured.
            PublicationNotFoundError: If publication is not found.
            PublicatiebankError: For other API errors.
        """
        if not self.is_configured:
            raise PublicatiebankNotConfiguredError("GPP_PUBLICATIEBANK_URL is not configured")

        client = await self._get_client()
        url = f"/api/v2/publicaties/{publication_uuid}"

        logger.info("Fetching publication metadata", uuid=str(publication_uuid), url=url)

        try:
            response = await client.get(url)

            if response.status_code == 404:
                raise PublicationNotFoundError(f"Publication {publication_uuid} not found in publicatiebank")

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error("Publicatiebank API error", status_code=e.response.status_code, detail=e.response.text)
            raise PublicatiebankError(f"Publicatiebank API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error("Publicatiebank request failed", error=str(e))
            raise PublicatiebankError(f"Failed to connect to publicatiebank: {e}") from e

    async def get_publication_documents(self, publication_uuid: str | UUID) -> list[dict]:
        """Get documents for a publication from publicatiebank.

        Args:
            publication_uuid: UUID of the publication.

        Returns:
            List of document metadata dicts.

        Raises:
            PublicatiebankNotConfiguredError: If publicatiebank is not configured.
            PublicatiebankError: For API errors.
        """
        if not self.is_configured:
            raise PublicatiebankNotConfiguredError("GPP_PUBLICATIEBANK_URL is not configured")

        client = await self._get_client()
        url = "/api/v2/documenten"
        params = {"publicatie": str(publication_uuid)}

        logger.info("Fetching publication documents", publication_uuid=str(publication_uuid))

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            # Handle paginated response
            if isinstance(data, dict) and "results" in data:
                return data["results"]
            return data

        except httpx.HTTPStatusError as e:
            logger.error("Publicatiebank API error", status_code=e.response.status_code, detail=e.response.text)
            raise PublicatiebankError(f"Publicatiebank API error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error("Publicatiebank request failed", error=str(e))
            raise PublicatiebankError(f"Failed to connect to publicatiebank: {e}") from e

    async def get_publication_with_documents(
        self, publication_uuid: str | UUID, download_content: bool = True
    ) -> PublicatiebankPublication:
        """Get publication with all its documents from publicatiebank.

        Args:
            publication_uuid: UUID of the publication.
            download_content: Whether to download document content (default True).

        Returns:
            PublicatiebankPublication with metadata and documents.

        Raises:
            PublicatiebankNotConfiguredError: If publicatiebank is not configured.
            PublicationNotFoundError: If publication is not found.
            DocumentDownloadError: If document download fails.
        """
        # Fetch publication metadata
        pub_metadata = await self.get_publication_metadata(publication_uuid)

        # Fetch document list
        doc_list = await self.get_publication_documents(publication_uuid)

        # Fetch each document with content
        documents = []
        for doc_meta in doc_list:
            doc_uuid = doc_meta["uuid"]
            content = b""
            if download_content:
                try:
                    content = await self.download_document(doc_uuid)
                except DocumentDownloadError as e:
                    logger.warning(
                        "Failed to download document, skipping",
                        document_uuid=doc_uuid,
                        error=str(e),
                    )
                    continue

            documents.append(
                PublicatiebankDocument(
                    uuid=doc_meta["uuid"],
                    officiele_titel=doc_meta["officiele_titel"],
                    verkorte_titel=doc_meta.get("verkorte_titel"),
                    omschrijving=doc_meta.get("omschrijving"),
                    bestandsnaam=doc_meta["bestandsnaam"],
                    bestandsformaat=doc_meta["bestandsformaat"],
                    bestandsomvang=doc_meta["bestandsomvang"],
                    publicatiestatus=doc_meta["publicatiestatus"],
                    content=content,
                    kenmerken=doc_meta.get("kenmerken", []),
                )
            )

        logger.info(
            "Publication retrieved",
            uuid=str(publication_uuid),
            title=pub_metadata.get("officiele_titel"),
            document_count=len(documents),
        )

        return PublicatiebankPublication(
            uuid=pub_metadata["uuid"],
            officiele_titel=pub_metadata.get("officiele_titel", ""),
            verkorte_titel=pub_metadata.get("verkorte_titel"),
            omschrijving=pub_metadata.get("omschrijving"),
            publicatiestatus=pub_metadata.get("publicatiestatus", ""),
            publisher=pub_metadata.get("publisher"),
            informatie_categorieen=pub_metadata.get("informatie_categorieen", []),
            onderwerpen=pub_metadata.get("onderwerpen", []),
            kenmerken=pub_metadata.get("kenmerken", []),
            documents=documents,
        )
