"""Unit tests for the publicatiebank client."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from woo_hoo.services.publicatiebank_client import (
    DocumentDownloadError,
    DocumentNotFoundError,
    PublicatiebankClient,
    PublicatiebankDocument,
    PublicatiebankNotConfiguredError,
)


class TestPublicatiebankClientConfiguration:
    """Tests for client configuration."""

    def test_is_configured_false_when_no_url(self):
        """Should return False when no URL is configured."""
        with patch("woo_hoo.services.publicatiebank_client.get_settings") as mock_settings:
            mock_settings.return_value.gpp_publicatiebank_url = None
            mock_settings.return_value.gpp_api_token = None

            client = PublicatiebankClient()
            assert client.is_configured is False

    def test_is_configured_true_when_url_set(self):
        """Should return True when URL is configured."""
        with patch("woo_hoo.services.publicatiebank_client.get_settings") as mock_settings:
            mock_settings.return_value.gpp_publicatiebank_url = "http://localhost:8080"
            mock_settings.return_value.gpp_api_token = None

            client = PublicatiebankClient()
            assert client.is_configured is True

    def test_explicit_url_overrides_settings(self):
        """Explicit URL should override settings."""
        with patch("woo_hoo.services.publicatiebank_client.get_settings") as mock_settings:
            mock_settings.return_value.gpp_publicatiebank_url = "http://settings-url.com"
            mock_settings.return_value.gpp_api_token = None

            client = PublicatiebankClient(base_url="http://explicit-url.com")
            assert client.base_url == "http://explicit-url.com"


class TestGetDocumentMetadata:
    """Tests for get_document_metadata method."""

    @pytest.mark.asyncio
    async def test_raises_when_not_configured(self):
        """Should raise PublicatiebankNotConfiguredError when not configured."""
        with patch("woo_hoo.services.publicatiebank_client.get_settings") as mock_settings:
            mock_settings.return_value.gpp_publicatiebank_url = None
            mock_settings.return_value.gpp_api_token = None

            client = PublicatiebankClient()

            with pytest.raises(PublicatiebankNotConfiguredError):
                await client.get_document_metadata("test-uuid")

    @pytest.mark.asyncio
    async def test_returns_metadata_on_success(self):
        """Should return document metadata on successful request."""
        mock_metadata = {
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "officiele_titel": "Test Document",
            "bestandsnaam": "test.pdf",
        }

        with patch("woo_hoo.services.publicatiebank_client.get_settings") as mock_settings:
            mock_settings.return_value.gpp_publicatiebank_url = "http://localhost:8080"
            mock_settings.return_value.gpp_api_token = "test-token"

            client = PublicatiebankClient()

            # Create a proper mock response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = lambda: mock_metadata
            mock_response.raise_for_status = lambda: None

            # Mock the _get_client to return a mock http client
            mock_http_client = AsyncMock()
            mock_http_client.get = AsyncMock(return_value=mock_response)

            with patch.object(client, "_get_client", return_value=mock_http_client):
                result = await client.get_document_metadata("550e8400-e29b-41d4-a716-446655440000")

        assert result["uuid"] == "550e8400-e29b-41d4-a716-446655440000"
        assert result["officiele_titel"] == "Test Document"

    @pytest.mark.asyncio
    async def test_raises_not_found_on_404(self):
        """Should raise DocumentNotFoundError on 404 response."""
        with patch("woo_hoo.services.publicatiebank_client.get_settings") as mock_settings:
            mock_settings.return_value.gpp_publicatiebank_url = "http://localhost:8080"
            mock_settings.return_value.gpp_api_token = None

            client = PublicatiebankClient()

            with patch.object(client, "_get_client") as mock_get_client:
                mock_http_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status_code = 404
                mock_http_client.get = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_http_client

                with pytest.raises(DocumentNotFoundError):
                    await client.get_document_metadata("nonexistent-uuid")


class TestDownloadDocument:
    """Tests for download_document method."""

    @pytest.mark.asyncio
    async def test_raises_when_not_configured(self):
        """Should raise PublicatiebankNotConfiguredError when not configured."""
        with patch("woo_hoo.services.publicatiebank_client.get_settings") as mock_settings:
            mock_settings.return_value.gpp_publicatiebank_url = None
            mock_settings.return_value.gpp_api_token = None

            client = PublicatiebankClient()

            with pytest.raises(PublicatiebankNotConfiguredError):
                await client.download_document("test-uuid")

    @pytest.mark.asyncio
    async def test_returns_content_on_success(self):
        """Should return document content on successful download."""
        mock_content = b"PDF content here"

        with patch("woo_hoo.services.publicatiebank_client.get_settings") as mock_settings:
            mock_settings.return_value.gpp_publicatiebank_url = "http://localhost:8080"
            mock_settings.return_value.gpp_api_token = None

            client = PublicatiebankClient()

            with patch.object(client, "_get_client") as mock_get_client:
                mock_http_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.content = mock_content
                mock_response.raise_for_status = lambda: None
                mock_http_client.get = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_http_client

                result = await client.download_document("test-uuid")

        assert result == mock_content

    @pytest.mark.asyncio
    async def test_raises_on_409_conflict(self):
        """Should raise DocumentDownloadError on 409 (upload not completed)."""
        with patch("woo_hoo.services.publicatiebank_client.get_settings") as mock_settings:
            mock_settings.return_value.gpp_publicatiebank_url = "http://localhost:8080"
            mock_settings.return_value.gpp_api_token = None

            client = PublicatiebankClient()

            with patch.object(client, "_get_client") as mock_get_client:
                mock_http_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.status_code = 409
                mock_http_client.get = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_http_client

                with pytest.raises(DocumentDownloadError) as exc_info:
                    await client.download_document("test-uuid")

                assert "not yet completed" in str(exc_info.value)


class TestGetDocument:
    """Tests for get_document method (combined metadata + content)."""

    @pytest.mark.asyncio
    async def test_returns_complete_document(self):
        """Should return PublicatiebankDocument with metadata and content."""
        mock_metadata = {
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "officiele_titel": "Test Document",
            "verkorte_titel": "Test",
            "omschrijving": "A test document",
            "bestandsnaam": "test.pdf",
            "bestandsformaat": "application/pdf",
            "bestandsomvang": 1024,
            "publicatiestatus": "published",
            "kenmerken": [{"kenmerk": "TEST-001", "bron": "test"}],
        }
        mock_content = b"PDF content"

        with patch("woo_hoo.services.publicatiebank_client.get_settings") as mock_settings:
            mock_settings.return_value.gpp_publicatiebank_url = "http://localhost:8080"
            mock_settings.return_value.gpp_api_token = None

            client = PublicatiebankClient()

            with (
                patch.object(client, "get_document_metadata", return_value=mock_metadata),
                patch.object(client, "download_document", return_value=mock_content),
            ):
                result = await client.get_document("550e8400-e29b-41d4-a716-446655440000")

        assert isinstance(result, PublicatiebankDocument)
        assert result.uuid == "550e8400-e29b-41d4-a716-446655440000"
        assert result.officiele_titel == "Test Document"
        assert result.content == mock_content
        assert result.kenmerken == [{"kenmerk": "TEST-001", "bron": "test"}]
