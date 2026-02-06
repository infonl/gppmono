"""Tests for GppApiClient service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from gpp_app.auth.oidc import OdpcUser
from gpp_app.services.gpp_api_client import GppApiClient, get_gpp_api_client, normalize_to_ascii


class TestNormalizeToAscii:
    """Tests for normalize_to_ascii function."""

    def test_ascii_unchanged(self):
        """ASCII text passes through unchanged."""
        assert normalize_to_ascii("Hello World") == "Hello World"

    def test_unicode_normalized(self):
        """Unicode characters are normalized."""
        assert normalize_to_ascii("Café") == "Cafe"
        assert normalize_to_ascii("naïve") == "naive"

    def test_special_chars_preserved(self):
        """Some special characters are preserved."""
        result = normalize_to_ascii("Test-Name_123")
        assert "Test" in result
        assert "Name" in result

    def test_none_returns_empty(self):
        """None returns empty string."""
        assert normalize_to_ascii(None) == ""

    def test_empty_returns_empty(self):
        """Empty string returns empty string."""
        assert normalize_to_ascii("") == ""


class TestGppApiClient:
    """Tests for GppApiClient."""

    @pytest.fixture
    def mock_user(self) -> OdpcUser:
        """Create a mock user."""
        return OdpcUser(
            is_logged_in=True,
            is_admin=False,
            id="user-123",
            full_name="Test User",
            email="user@test.nl",
            roles=[],
        )

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.gpp_api_base_url = "http://gpp-api.test:8000"
        settings.gpp_api_token = "test-token"
        return settings

    @pytest.fixture
    def client(self, mock_user, mock_settings) -> GppApiClient:
        """Create a GppApiClient instance with mocked settings."""
        # Inject httpx client directly to avoid needing settings for client creation
        http_client = httpx.AsyncClient(base_url=mock_settings.gpp_api_base_url, timeout=60.0)
        return GppApiClient(user=mock_user, client=http_client)

    @respx.mock
    async def test_get_request(self, client, mock_settings):
        """Makes GET request with correct headers."""
        respx.get("http://gpp-api.test:8000/api/v2/test").mock(
            return_value=httpx.Response(200, json={"result": "ok"})
        )

        with patch("gpp_app.services.gpp_api_client.get_settings", return_value=mock_settings):
            response = await client.get("/api/v2/test", action="test_action")

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "ok"
        await client.close()

    @respx.mock
    async def test_post_request(self, client, mock_settings):
        """Makes POST request with correct headers."""
        respx.post("http://gpp-api.test:8000/api/v2/test").mock(
            return_value=httpx.Response(201, json={"id": "123"})
        )

        with patch("gpp_app.services.gpp_api_client.get_settings", return_value=mock_settings):
            response = await client.post(
                "/api/v2/test",
                json={"name": "test"},
                action="test_action",
            )

        assert response.status_code == 201
        await client.close()

    @respx.mock
    async def test_put_request(self, client, mock_settings):
        """Makes PUT request with correct headers."""
        respx.put("http://gpp-api.test:8000/api/v2/test/123").mock(
            return_value=httpx.Response(200, json={"updated": True})
        )

        with patch("gpp_app.services.gpp_api_client.get_settings", return_value=mock_settings):
            response = await client.put(
                "/api/v2/test/123",
                json={"name": "updated"},
                action="test_action",
            )

        assert response.status_code == 200
        await client.close()

    @respx.mock
    async def test_delete_request(self, client, mock_settings):
        """Makes DELETE request with correct headers."""
        respx.delete("http://gpp-api.test:8000/api/v2/test/123").mock(
            return_value=httpx.Response(204)
        )

        with patch("gpp_app.services.gpp_api_client.get_settings", return_value=mock_settings):
            response = await client.delete("/api/v2/test/123", action="test_action")

        assert response.status_code == 204
        await client.close()

    @respx.mock
    async def test_includes_audit_headers(self, client, mock_settings):
        """Includes audit headers in requests."""
        route = respx.get("http://gpp-api.test:8000/api/v2/test").mock(
            return_value=httpx.Response(200, json={})
        )

        with patch("gpp_app.services.gpp_api_client.get_settings", return_value=mock_settings):
            await client.get("/api/v2/test", action="test")
        await client.close()

        # Check that headers were sent
        assert route.called
        request = route.calls[0].request
        assert "Audit-User-ID" in request.headers
        assert "Audit-User-Representation" in request.headers


class TestGetGppApiClient:
    """Tests for get_gpp_api_client factory."""

    def test_creates_client(self):
        """Creates a GppApiClient instance."""
        user = OdpcUser(
            is_logged_in=True,
            is_admin=False,
            id="user-123",
            full_name="Test User",
            email="user@test.nl",
            roles=[],
        )

        client = get_gpp_api_client(user)

        assert isinstance(client, GppApiClient)
