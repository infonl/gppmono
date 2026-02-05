"""Pytest configuration and fixtures."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

# Set test environment variables before importing app
os.environ.setdefault("OPENROUTER_API_KEY", "test-api-key-for-testing")
os.environ.setdefault("LOG_FORMAT", "console")
os.environ.setdefault("LOG_LEVEL", "DEBUG")

from woo_hoo.main import app


@pytest.fixture
def sample_document_text() -> str:
    """Sample Dutch government document text for testing."""
    return """
    Gemeente Amsterdam
    Bestuursdienst

    Ref: BD/2024/12345
    Datum: 15 januari 2024

    Aan: College van Burgemeester en Wethouders

    Betreft: Advies inzake wijziging bestemmingsplan Centrum

    Geacht college,

    Hierbij ontvangt u ons advies inzake de voorgenomen wijziging van het bestemmingsplan
    voor het centrumgebied. Na zorgvuldige analyse van de ingediende plannen en de
    reacties uit de inspraakprocedure, adviseren wij als volgt.

    1. Samenvatting
    Het voorgestelde bestemmingsplan voorziet in uitbreiding van de horeca-mogelijkheden
    in de binnenstad. Wij achten dit in lijn met het coalitieakkoord en de economische
    visie 2030.

    2. Overwegingen
    - De inspraak heeft 45 reacties opgeleverd
    - Meerderheid is positief over het plan
    - Enkele zorgen over geluidsoverlast

    3. Advies
    Wij adviseren het college om het bestemmingsplan vast te stellen met inachtneming
    van de volgende aanpassingen:
    - Aanscherping geluidsvoorschriften
    - Monitoring na 1 jaar

    Met vriendelijke groet,

    Drs. J. de Vries
    Directeur Bestuursdienst
    """


@pytest.fixture
def sample_publisher_hint() -> dict:
    """Sample publisher hint for testing."""
    return {
        "name": "Gemeente Amsterdam",
        "tooi_uri": "https://identifier.overheid.nl/tooi/id/gemeente/gm0363",
    }


@pytest.fixture
def minimal_valid_metadata() -> dict:
    """Minimal valid DIWOO metadata for testing."""
    return {
        "publisher": {
            "resource": "https://identifier.overheid.nl/tooi/id/gemeente/gm0363",
            "label": "Gemeente Amsterdam",
        },
        "titelcollectie": {
            "officieleTitel": "Test Document",
        },
        "classificatiecollectie": {
            "informatiecategorieen": [
                {"categorie": "c_5ba23c01"},  # ADVIEZEN TOOI identifier
            ],
        },
        "documenthandelingen": [
            {
                "soortHandeling": {"handeling": "c_registratie"},  # REGISTRATIE TOOI identifier
                "atTime": "2024-01-15T10:00:00Z",
            },
        ],
    }


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for e2e testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
