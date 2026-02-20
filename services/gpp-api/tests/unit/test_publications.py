"""Tests for publication endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from gpp_api.db.models import Publication, PublicationStatus


class TestListPublications:
    """Tests for GET /api/v2/publicaties."""

    async def test_list_empty(self, client: AsyncClient):
        """Returns empty list when no publications exist."""
        response = await client.get("/api/v2/publicaties")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["results"] == []

    async def test_list_with_publications(self, client: AsyncClient, test_session, test_eigenaar, publication_data):
        """Returns list of publications."""
        # Create test publications
        pub1 = Publication(**publication_data(officiele_titel="Publication A", eigenaar_id=test_eigenaar.id))
        pub2 = Publication(**publication_data(officiele_titel="Publication B", eigenaar_id=test_eigenaar.id))
        test_session.add_all([pub1, pub2])
        await test_session.commit()

        response = await client.get("/api/v2/publicaties")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["results"]) == 2

    async def test_list_pagination(self, client: AsyncClient, test_session, test_eigenaar, publication_data):
        """Pagination works correctly."""
        # Create 5 publications
        for i in range(5):
            pub = Publication(**publication_data(officiele_titel=f"Publication {i}", eigenaar_id=test_eigenaar.id))
            test_session.add(pub)
        await test_session.commit()

        # Request first page with 2 items
        response = await client.get("/api/v2/publicaties?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 5
        assert len(data["results"]) == 2


class TestGetPublication:
    """Tests for GET /api/v2/publicaties/{uuid}."""

    async def test_get_existing(self, client: AsyncClient, test_session, test_eigenaar, publication_data):
        """Returns publication when it exists."""
        pub = Publication(**publication_data(officiele_titel="Test Publication", eigenaar_id=test_eigenaar.id))
        test_session.add(pub)
        await test_session.commit()
        await test_session.refresh(pub)

        response = await client.get(f"/api/v2/publicaties/{pub.uuid}")

        assert response.status_code == 200
        data = response.json()
        assert data["officieleTitel"] == "Test Publication"

    async def test_get_nonexistent(self, client: AsyncClient):
        """Returns 404 for non-existent publication."""
        fake_uuid = str(uuid.uuid4())

        response = await client.get(f"/api/v2/publicaties/{fake_uuid}")

        assert response.status_code == 404


class TestCreatePublication:
    """Tests for POST /api/v2/publicaties."""

    async def test_create_minimal(self, client: AsyncClient):
        """Creates publication with minimal data."""
        response = await client.post(
            "/api/v2/publicaties",
            json={
                "officieleTitel": "New Publication",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["officieleTitel"] == "New Publication"
        assert data["publicatiestatus"] == "concept"
        assert "uuid" in data

    async def test_create_with_all_fields(self, client: AsyncClient):
        """Creates publication with all fields."""
        response = await client.post(
            "/api/v2/publicaties",
            json={
                "officieleTitel": "Full Publication",
                "verkorteTitel": "Full Pub",
                "omschrijving": "A detailed description",
                "publicatiestatus": "concept",
                "informatieCategorieen": [],
                "onderwerpen": [],
                "kenmerken": [
                    {"kenmerk": "test-kenmerk", "bron": "test-bron"}
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["officieleTitel"] == "Full Publication"
        assert data["verkorteTitel"] == "Full Pub"
        assert data["omschrijving"] == "A detailed description"
        assert len(data["kenmerken"]) == 1


class TestUpdatePublication:
    """Tests for PUT /api/v2/publicaties/{uuid}."""

    async def test_update_title(self, client: AsyncClient, test_session, test_eigenaar, publication_data):
        """Updates publication title."""
        pub = Publication(**publication_data(officiele_titel="Original Title", eigenaar_id=test_eigenaar.id))
        test_session.add(pub)
        await test_session.commit()
        await test_session.refresh(pub)

        response = await client.put(
            f"/api/v2/publicaties/{pub.uuid}",
            json={
                "officieleTitel": "Updated Title",
                "verkorteTitel": "",
                "omschrijving": "",
                "publicatiestatus": "concept",
                "publisher": "",
                "verantwoordelijke": "",
                "informatieCategorieen": [],
                "onderwerpen": [],
                "kenmerken": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["officieleTitel"] == "Updated Title"

    async def test_update_nonexistent(self, client: AsyncClient):
        """Returns 404 for non-existent publication."""
        fake_uuid = str(uuid.uuid4())

        response = await client.put(
            f"/api/v2/publicaties/{fake_uuid}",
            json={
                "officieleTitel": "Test",
                "verkorteTitel": "",
                "omschrijving": "",
                "publicatiestatus": "concept",
                "publisher": "",
                "verantwoordelijke": "",
                "informatieCategorieen": [],
                "onderwerpen": [],
                "kenmerken": [],
            },
        )

        assert response.status_code == 404


class TestDeletePublication:
    """Tests for DELETE /api/v2/publicaties/{uuid}."""

    async def test_delete_existing(self, client: AsyncClient, test_session, test_eigenaar, publication_data):
        """Deletes existing publication."""
        pub = Publication(**publication_data(eigenaar_id=test_eigenaar.id))
        test_session.add(pub)
        await test_session.commit()
        await test_session.refresh(pub)

        response = await client.delete(f"/api/v2/publicaties/{pub.uuid}")

        assert response.status_code == 204

    async def test_delete_nonexistent(self, client: AsyncClient):
        """Returns 404 for non-existent publication."""
        fake_uuid = str(uuid.uuid4())

        response = await client.delete(f"/api/v2/publicaties/{fake_uuid}")

        assert response.status_code == 404


class TestPublishPublication:
    """Tests for POST /api/v2/publicaties/{uuid}/publish."""

    async def test_publish_concept(
        self, client: AsyncClient, test_session, test_eigenaar, test_publisher, publication_data
    ):
        """Publishes a concept publication."""
        # Publisher is required for gepubliceerd status (CHECK constraint)
        pub = Publication(
            **publication_data(
                publicatiestatus="concept",
                eigenaar_id=test_eigenaar.id,
                publisher_id=test_publisher.id,
            )
        )
        test_session.add(pub)
        await test_session.commit()
        await test_session.refresh(pub)

        response = await client.post(f"/api/v2/publicaties/{pub.uuid}/publish")

        assert response.status_code == 200
        data = response.json()
        assert data["publicatiestatus"] == "gepubliceerd"

    async def test_publish_already_published(
        self, client: AsyncClient, test_session, test_eigenaar, test_publisher, publication_data
    ):
        """Returns error when already published."""
        pub = Publication(
            **publication_data(
                publicatiestatus="gepubliceerd",
                eigenaar_id=test_eigenaar.id,
                publisher_id=test_publisher.id,
            )
        )
        test_session.add(pub)
        await test_session.commit()
        await test_session.refresh(pub)

        response = await client.post(f"/api/v2/publicaties/{pub.uuid}/publish")

        assert response.status_code == 400


class TestRevokePublication:
    """Tests for POST /api/v2/publicaties/{uuid}/revoke."""

    async def test_revoke_published(
        self, client: AsyncClient, test_session, test_eigenaar, test_publisher, publication_data
    ):
        """Revokes a published publication."""
        pub = Publication(
            **publication_data(
                publicatiestatus="gepubliceerd",
                gepubliceerd_op=datetime.now(timezone.utc),
                eigenaar_id=test_eigenaar.id,
                publisher_id=test_publisher.id,
            )
        )
        test_session.add(pub)
        await test_session.commit()
        await test_session.refresh(pub)

        response = await client.post(f"/api/v2/publicaties/{pub.uuid}/revoke")

        assert response.status_code == 200
        data = response.json()
        assert data["publicatiestatus"] == "ingetrokken"

    async def test_revoke_concept(self, client: AsyncClient, test_session, test_eigenaar, publication_data):
        """Returns error when revoking a concept."""
        pub = Publication(**publication_data(publicatiestatus="concept", eigenaar_id=test_eigenaar.id))
        test_session.add(pub)
        await test_session.commit()
        await test_session.refresh(pub)

        response = await client.post(f"/api/v2/publicaties/{pub.uuid}/revoke")

        assert response.status_code == 400
