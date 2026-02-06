"""Tests for user groups endpoints."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from gpp_app.db.models import Gebruikersgroep, GebruikersgroepGebruiker


class TestListUserGroups:
    """Tests for GET /api/gebruikersgroepen."""

    async def test_list_empty(self, admin_client: AsyncClient):
        """Returns empty list when no groups exist."""
        response = await admin_client.get("/api/gebruikersgroepen")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    async def test_list_with_groups(self, admin_client: AsyncClient, test_session):
        """Returns list of user groups."""
        # Create test groups
        group1 = Gebruikersgroep(naam="Group 1", omschrijving="First group")
        group2 = Gebruikersgroep(naam="Group 2", omschrijving="Second group")
        test_session.add_all([group1, group2])
        await test_session.commit()

        response = await admin_client.get("/api/gebruikersgroepen")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_list_requires_auth(self, client: AsyncClient):
        """Non-admin users can still list groups."""
        response = await client.get("/api/gebruikersgroepen")

        # Regular users can list groups too
        assert response.status_code == 200


class TestGetUserGroup:
    """Tests for GET /api/gebruikersgroepen/{uuid}."""

    async def test_get_existing(self, admin_client: AsyncClient, test_session):
        """Returns group when it exists."""
        group = Gebruikersgroep(naam="Test Group", omschrijving="Test description")
        test_session.add(group)
        await test_session.commit()
        await test_session.refresh(group)

        response = await admin_client.get(f"/api/gebruikersgroepen/{group.uuid}")

        assert response.status_code == 200
        data = response.json()
        assert data["naam"] == "Test Group"
        assert data["omschrijving"] == "Test description"

    async def test_get_nonexistent(self, admin_client: AsyncClient):
        """Returns 404 for non-existent group."""
        fake_uuid = str(uuid.uuid4())

        response = await admin_client.get(f"/api/gebruikersgroepen/{fake_uuid}")

        assert response.status_code == 404


class TestCreateUserGroup:
    """Tests for POST /api/gebruikersgroepen."""

    async def test_create_minimal(self, admin_client: AsyncClient):
        """Creates group with minimal data."""
        response = await admin_client.post(
            "/api/gebruikersgroepen",
            json={"naam": "New Group"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["naam"] == "New Group"
        assert "uuid" in data

    async def test_create_with_description(self, admin_client: AsyncClient):
        """Creates group with description."""
        response = await admin_client.post(
            "/api/gebruikersgroepen",
            json={
                "naam": "Full Group",
                "omschrijving": "A detailed description",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["naam"] == "Full Group"
        assert data["omschrijving"] == "A detailed description"

    async def test_create_duplicate_name_fails(self, admin_client: AsyncClient, test_session):
        """Cannot create group with duplicate name."""
        # Create existing group
        group = Gebruikersgroep(naam="Existing Group")
        test_session.add(group)
        await test_session.commit()

        response = await admin_client.post(
            "/api/gebruikersgroepen",
            json={"naam": "Existing Group"},
        )

        assert response.status_code == 409  # Conflict


class TestUpdateUserGroup:
    """Tests for PUT /api/gebruikersgroepen/{uuid}."""

    async def test_update_name(self, admin_client: AsyncClient, test_session):
        """Updates group name."""
        group = Gebruikersgroep(naam="Original Name")
        test_session.add(group)
        await test_session.commit()
        await test_session.refresh(group)

        response = await admin_client.put(
            f"/api/gebruikersgroepen/{group.uuid}",
            json={"naam": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["naam"] == "Updated Name"

    async def test_update_nonexistent(self, admin_client: AsyncClient):
        """Returns 404 for non-existent group."""
        fake_uuid = str(uuid.uuid4())

        response = await admin_client.put(
            f"/api/gebruikersgroepen/{fake_uuid}",
            json={"naam": "Test"},
        )

        assert response.status_code == 404


class TestDeleteUserGroup:
    """Tests for DELETE /api/gebruikersgroepen/{uuid}."""

    async def test_delete_existing(self, admin_client: AsyncClient, test_session):
        """Deletes existing group."""
        group = Gebruikersgroep(naam="To Delete")
        test_session.add(group)
        await test_session.commit()
        await test_session.refresh(group)

        response = await admin_client.delete(f"/api/gebruikersgroepen/{group.uuid}")

        assert response.status_code == 204

    async def test_delete_nonexistent(self, admin_client: AsyncClient):
        """Returns 404 for non-existent group."""
        fake_uuid = str(uuid.uuid4())

        response = await admin_client.delete(f"/api/gebruikersgroepen/{fake_uuid}")

        assert response.status_code == 404


class TestMyUserGroups:
    """Tests for GET /api/mijn-gebruikersgroepen."""

    async def test_returns_user_groups(self, client: AsyncClient, test_session, dev_user):
        """Returns groups the user belongs to."""
        # Create group and add user to it
        group = Gebruikersgroep(naam="User's Group")
        test_session.add(group)
        await test_session.commit()
        await test_session.refresh(group)

        membership = GebruikersgroepGebruiker(
            gebruikersgroep_uuid=group.uuid,
            gebruiker_id=dev_user.id,  # Use .id not .identifier
        )
        test_session.add(membership)
        await test_session.commit()

        response = await client.get("/api/mijn-gebruikersgroepen")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["naam"] == "User's Group"

    async def test_returns_empty_when_no_groups(self, client: AsyncClient):
        """Returns empty list when user has no groups."""
        response = await client.get("/api/mijn-gebruikersgroepen")

        assert response.status_code == 200
        data = response.json()
        assert data == []
