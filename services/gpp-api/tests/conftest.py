"""Pytest configuration and fixtures."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from gpp_api.main import create_app


@pytest.fixture
def app():
    """Create a test application."""
    return create_app()


@pytest.fixture
async def client(app):
    """Create an async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
