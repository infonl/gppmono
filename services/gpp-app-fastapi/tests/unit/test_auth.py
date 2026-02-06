"""Tests for authentication endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_me_endpoint_dev_mode(client):
    """Test /api/me returns dev user in dev mode."""
    response = await client.get("/api/me")
    assert response.status_code == 200
    data = response.json()

    # In dev mode (no OIDC configured), should return dev user
    assert data["is_logged_in"] is True
    assert data["is_admin"] is True
    assert data["id"] == "dev-user"
    assert data["full_name"] == "Development User"
