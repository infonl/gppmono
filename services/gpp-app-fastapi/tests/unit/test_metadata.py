"""Tests for metadata endpoints."""

from __future__ import annotations

import uuid

from httpx import AsyncClient


class TestMetadataHealth:
    """Tests for GET /api/v1/metadata/health."""

    async def test_health_check_success(self, client: AsyncClient, _mock_woo_hoo):
        """Returns available when woo-hoo is healthy."""
        response = await client.get("/api/v1/metadata/health")

        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert "woo-hoo" in data["message"]

    async def test_health_check_woo_hoo_down(self, client: AsyncClient):
        """Returns unavailable when woo-hoo is down."""
        # No mock - will fail to connect
        response = await client.get("/api/v1/metadata/health")

        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False


class TestMetadataGenerate:
    """Tests for POST /api/v1/metadata/generate/{document_uuid}."""

    async def test_generate_success(self, client: AsyncClient, _mock_woo_hoo):
        """Successfully generates metadata for a document."""
        doc_uuid = str(uuid.uuid4())

        response = await client.post(f"/api/v1/metadata/generate/{doc_uuid}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["suggestion"] is not None
        assert data["suggestion"]["metadata"]["titelcollectie"]["officieleTitel"] == "Generated Title"

    async def test_generate_returns_error_on_failure(self, client: AsyncClient):
        """Returns error when woo-hoo fails."""
        # No mock - will fail to connect
        doc_uuid = str(uuid.uuid4())

        response = await client.post(f"/api/v1/metadata/generate/{doc_uuid}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] is not None

    async def test_generate_response_format(self, client: AsyncClient, _mock_woo_hoo):
        """Response has correct format for frontend compatibility."""
        doc_uuid = str(uuid.uuid4())

        response = await client.post(f"/api/v1/metadata/generate/{doc_uuid}")

        assert response.status_code == 200
        data = response.json()

        # Check all required fields exist
        assert "success" in data
        assert "suggestion" in data
        assert "error" in data

        # Check suggestion structure
        if data["suggestion"]:
            assert "metadata" in data["suggestion"]
