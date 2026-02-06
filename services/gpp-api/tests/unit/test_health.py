"""Tests for health endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint returns healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "gpp-api"
    assert "version" in data


@pytest.mark.asyncio
async def test_readiness_check(client):
    """Test readiness check endpoint."""
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "gpp-api"
    assert "database" in data
    assert "redis" in data
