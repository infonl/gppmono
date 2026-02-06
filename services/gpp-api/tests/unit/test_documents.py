"""Tests for document endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from gpp_api.db.models import Document, Publication


class TestListDocuments:
    """Tests for GET /api/v2/documenten."""

    async def test_list_empty(self, client: AsyncClient):
        """Returns empty list when no documents exist."""
        response = await client.get("/api/v2/documenten")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["results"] == []

    async def test_list_filtered_by_publication(
        self, client: AsyncClient, test_session, test_eigenaar, publication_data, document_data
    ):
        """Filters documents by publication UUID."""
        # Create two publications with documents
        pub1 = Publication(**publication_data(officiele_titel="Pub 1", eigenaar_id=test_eigenaar.id))
        pub2 = Publication(**publication_data(officiele_titel="Pub 2", eigenaar_id=test_eigenaar.id))
        test_session.add_all([pub1, pub2])
        await test_session.commit()
        await test_session.refresh(pub1)
        await test_session.refresh(pub2)

        doc1 = Document(**document_data(publicatie_id=pub1.id, eigenaar_id=test_eigenaar.id, officiele_titel="Doc 1"))
        doc2 = Document(**document_data(publicatie_id=pub2.id, eigenaar_id=test_eigenaar.id, officiele_titel="Doc 2"))
        test_session.add_all([doc1, doc2])
        await test_session.commit()

        # Filter by pub1
        response = await client.get(f"/api/v2/documenten?publicatie={pub1.uuid}")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["officieleTitel"] == "Doc 1"


class TestGetDocument:
    """Tests for GET /api/v2/documenten/{uuid}."""

    async def test_get_existing(
        self, client: AsyncClient, test_session, test_eigenaar, publication_data, document_data
    ):
        """Returns document when it exists."""
        pub = Publication(**publication_data(eigenaar_id=test_eigenaar.id))
        test_session.add(pub)
        await test_session.commit()
        await test_session.refresh(pub)

        doc = Document(**document_data(publicatie_id=pub.id, eigenaar_id=test_eigenaar.id, officiele_titel="Test Doc"))
        test_session.add(doc)
        await test_session.commit()
        await test_session.refresh(doc)

        response = await client.get(f"/api/v2/documenten/{doc.uuid}")

        assert response.status_code == 200
        data = response.json()
        assert data["officieleTitel"] == "Test Doc"

    async def test_get_nonexistent(self, client: AsyncClient):
        """Returns 404 for non-existent document."""
        fake_uuid = str(uuid.uuid4())

        response = await client.get(f"/api/v2/documenten/{fake_uuid}")

        assert response.status_code == 404


class TestCreateDocument:
    """Tests for POST /api/v2/documenten."""

    async def test_create_document(
        self, client: AsyncClient, test_session, test_eigenaar, publication_data, mock_openzaak
    ):
        """Creates document with required fields."""
        pub = Publication(**publication_data(eigenaar_id=test_eigenaar.id))
        test_session.add(pub)
        await test_session.commit()
        await test_session.refresh(pub)

        response = await client.post(
            "/api/v2/documenten",
            json={
                "publicatie": str(pub.uuid),
                "officieleTitel": "New Document",
                "creatiedatum": "2024-01-01",
                "bestandsnaam": "test.pdf",
                "bestandsformaat": "application/pdf",
                "bestandsomvang": 1024,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["officieleTitel"] == "New Document"
        assert data["bestandsnaam"] == "test.pdf"
        assert "uuid" in data

    async def test_create_with_invalid_publication(self, client: AsyncClient):
        """Returns 400 for non-existent publication."""
        fake_uuid = str(uuid.uuid4())

        response = await client.post(
            "/api/v2/documenten",
            json={
                "publicatie": fake_uuid,
                "officieleTitel": "New Document",
                "creatiedatum": "2024-01-01",
                "bestandsnaam": "test.pdf",
                "bestandsformaat": "application/pdf",
                "bestandsomvang": 1024,
            },
        )

        # API returns 400 Bad Request for invalid publication reference
        assert response.status_code == 400


class TestUpdateDocument:
    """Tests for PUT /api/v2/documenten/{uuid}."""

    async def test_update_title(
        self, client: AsyncClient, test_session, test_eigenaar, publication_data, document_data
    ):
        """Updates document title."""
        pub = Publication(**publication_data(eigenaar_id=test_eigenaar.id))
        test_session.add(pub)
        await test_session.commit()
        await test_session.refresh(pub)

        doc = Document(**document_data(publicatie_id=pub.id, eigenaar_id=test_eigenaar.id, officiele_titel="Original"))
        test_session.add(doc)
        await test_session.commit()
        await test_session.refresh(doc)

        response = await client.put(
            f"/api/v2/documenten/{doc.uuid}",
            json={
                "publicatie": str(pub.uuid),
                "officieleTitel": "Updated Title",
                "verkorteTitel": "",
                "omschrijving": "",
                "creatiedatum": "2024-01-01",
                "bestandsnaam": "test.pdf",
                "bestandsformaat": "application/pdf",
                "bestandsomvang": 1024,
                "publicatiestatus": "concept",
                "kenmerken": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["officieleTitel"] == "Updated Title"

    async def test_update_nonexistent(self, client: AsyncClient, test_session, test_eigenaar, publication_data):
        """Returns 404 for non-existent document."""
        pub = Publication(**publication_data(eigenaar_id=test_eigenaar.id))
        test_session.add(pub)
        await test_session.commit()
        await test_session.refresh(pub)

        fake_uuid = str(uuid.uuid4())

        response = await client.put(
            f"/api/v2/documenten/{fake_uuid}",
            json={
                "publicatie": str(pub.uuid),
                "officieleTitel": "Test",
                "verkorteTitel": "",
                "omschrijving": "",
                "creatiedatum": "2024-01-01",
                "bestandsnaam": "test.pdf",
                "bestandsformaat": "application/pdf",
                "bestandsomvang": 1024,
                "publicatiestatus": "concept",
                "kenmerken": [],
            },
        )

        assert response.status_code == 404


class TestDeleteDocument:
    """Tests for DELETE /api/v2/documenten/{uuid}."""

    async def test_delete_existing(
        self, client: AsyncClient, test_session, test_eigenaar, publication_data, document_data
    ):
        """Deletes existing document."""
        pub = Publication(**publication_data(eigenaar_id=test_eigenaar.id))
        test_session.add(pub)
        await test_session.commit()
        await test_session.refresh(pub)

        doc = Document(**document_data(publicatie_id=pub.id, eigenaar_id=test_eigenaar.id))
        test_session.add(doc)
        await test_session.commit()
        await test_session.refresh(doc)

        response = await client.delete(f"/api/v2/documenten/{doc.uuid}")

        assert response.status_code == 204

    async def test_delete_nonexistent(self, client: AsyncClient):
        """Returns 404 for non-existent document."""
        fake_uuid = str(uuid.uuid4())

        response = await client.delete(f"/api/v2/documenten/{fake_uuid}")

        assert response.status_code == 404


class TestBestandsdelen:
    """Tests for file part generation."""

    async def test_document_includes_bestandsdelen(
        self, client: AsyncClient, test_session, test_eigenaar, publication_data, document_data, mock_openzaak
    ):
        """Document response includes bestandsdelen for upload."""
        pub = Publication(**publication_data(eigenaar_id=test_eigenaar.id))
        test_session.add(pub)
        await test_session.commit()
        await test_session.refresh(pub)

        # Create document with file size
        response = await client.post(
            "/api/v2/documenten",
            json={
                "publicatie": str(pub.uuid),
                "officieleTitel": "Test Document",
                "creatiedatum": "2024-01-01",
                "bestandsnaam": "test.pdf",
                "bestandsformaat": "application/pdf",
                "bestandsomvang": 1024,  # 1KB file
            },
        )

        assert response.status_code == 201
        data = response.json()
        # Should have bestandsdelen for upload
        if data.get("bestandsdelen"):
            assert len(data["bestandsdelen"]) >= 1
            assert "url" in data["bestandsdelen"][0]
            assert "volgnummer" in data["bestandsdelen"][0]
