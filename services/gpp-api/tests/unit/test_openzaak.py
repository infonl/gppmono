"""Tests for OpenZaak client."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
from httpx import Response

from gpp_api.services.openzaak import (
    OpenZaakClient,
    OpenZaakDocument,
    OpenZaakError,
    OpenZaakValidationError,
    create_zgw_jwt,
)


class TestCreateZgwJwt:
    """Tests for JWT creation."""

    def test_creates_valid_jwt(self):
        """JWT is created with correct structure."""
        token = create_zgw_jwt("test-client", "test-secret", "test-user")

        assert isinstance(token, str)
        # JWT has 3 parts separated by dots
        parts = token.split(".")
        assert len(parts) == 3

    def test_different_secrets_produce_different_tokens(self):
        """Different secrets produce different JWTs."""
        token1 = create_zgw_jwt("client", "secret1", "user")
        token2 = create_zgw_jwt("client", "secret2", "user")

        assert token1 != token2


class TestOpenZaakClient:
    """Tests for OpenZaakClient."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.openzaak_documents_api_url = "http://openzaak.test/documenten/api/v1"
        settings.openzaak_catalogi_api_url = "http://openzaak.test/catalogi/api/v1"
        settings.openzaak_client_id = "test-client"
        settings.openzaak_secret = "test-secret"
        return settings

    @pytest.fixture
    def client(self, mock_settings):
        """Create OpenZaak client with mocked settings."""
        return OpenZaakClient(settings=mock_settings)

    def test_get_informatieobjecttype_url(self, client):
        """Correctly constructs informatieobjecttype URL."""
        mock_category = MagicMock()
        mock_category.uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")

        url = client.get_informatieobjecttype_url(mock_category)

        assert url == "http://openzaak.test/catalogi/api/v1/informatieobjecttypen/12345678-1234-5678-1234-567812345678"

    @respx.mock
    async def test_create_document_success(self, client):
        """Successfully creates a document in OpenZaak."""
        doc_uuid = str(uuid.uuid4())
        respx.post("http://openzaak.test/documenten/api/v1/enkelvoudiginformatieobjecten").mock(
            return_value=Response(
                201,
                json={
                    "url": f"http://openzaak.test/documenten/api/v1/enkelvoudiginformatieobjecten/{doc_uuid}",
                    "identificatie": "DOC-001",
                    "bronorganisatie": "123456789",
                    "creatiedatum": "2024-01-01",
                    "titel": "Test",
                    "vertrouwelijkheidaanduiding": "openbaar",
                    "auteur": "Test",
                    "status": "definitief",
                    "formaat": "application/pdf",
                    "taal": "nld",
                    "bestandsnaam": "test.pdf",
                    "bestandsomvang": 1024,
                    "link": "",
                    "beschrijving": "",
                    "informatieobjecttype": "http://test/type",
                    "locked": False,
                    "lock": "",
                },
            )
        )

        result = await client.create_document(
            titel="Test",
            informatieobjecttype_url="http://test/type",
            bronorganisatie="123456789",
            creatiedatum="2024-01-01",
        )

        assert isinstance(result, OpenZaakDocument)
        assert result.titel == "Test"
        assert result.bronorganisatie == "123456789"
        await client.close()

    @respx.mock
    async def test_create_document_validation_error(self, client):
        """Raises validation error on 400 response."""
        respx.post("http://openzaak.test/documenten/api/v1/enkelvoudiginformatieobjecten").mock(
            return_value=Response(
                400,
                json={"informatieobjecttype": ["Invalid URL"]},
            )
        )

        with pytest.raises(OpenZaakValidationError) as exc_info:
            await client.create_document(
                titel="Test",
                informatieobjecttype_url="http://invalid",
                bronorganisatie="123",
                creatiedatum="2024-01-01",
            )

        assert "Validation failed" in str(exc_info.value)
        await client.close()

    @respx.mock
    async def test_lock_document(self, client):
        """Successfully locks a document."""
        doc_url = "http://openzaak.test/documenten/api/v1/enkelvoudiginformatieobjecten/test-uuid"
        respx.post(f"{doc_url}/lock").mock(
            return_value=Response(200, json={"lock": "abc123"})
        )

        lock = await client.lock_document(doc_url)

        assert lock == "abc123"
        await client.close()

    @respx.mock
    async def test_unlock_document(self, client):
        """Successfully unlocks a document."""
        doc_url = "http://openzaak.test/documenten/api/v1/enkelvoudiginformatieobjecten/test-uuid"
        respx.post(f"{doc_url}/unlock").mock(return_value=Response(204))

        # Should not raise
        await client.unlock_document(doc_url, "abc123")
        await client.close()

    @respx.mock
    async def test_upload_file_part(self, client):
        """Successfully uploads file content."""
        doc_url = "http://openzaak.test/documenten/api/v1/enkelvoudiginformatieobjecten/test-uuid"
        respx.patch(doc_url).mock(return_value=Response(200, json={}))

        # Should not raise
        await client.upload_file_part(doc_url, "lock123", b"file content")
        await client.close()

    @respx.mock
    async def test_download_document_content(self, client):
        """Successfully downloads document content."""
        doc_url = "http://openzaak.test/documenten/api/v1/enkelvoudiginformatieobjecten/test-uuid"
        respx.get(f"{doc_url}/download").mock(
            return_value=Response(200, content=b"PDF content")
        )

        content = await client.download_document_content(doc_url)

        assert content == b"PDF content"
        await client.close()
