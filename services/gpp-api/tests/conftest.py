"""Pytest configuration and fixtures for gpp-api tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from gpp_api.config import Settings, get_settings
import gpp_api.db.engine as db_engine_module
from gpp_api.api.deps import get_db
from gpp_api.db.models import Base
from gpp_api.main import create_app


# Test database URL - in-memory SQLite for fast tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def reset_engine_globals():
    """Reset engine globals before each test to avoid cross-test pollution."""
    # Reset the global engine and session factory
    db_engine_module._engine = None
    db_engine_module._session_factory = None
    yield
    # Clean up after test
    db_engine_module._engine = None
    db_engine_module._session_factory = None


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with mocked values."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        redis_url="redis://localhost:6379/15",
        openzaak_documents_api_url="http://openzaak.test/documenten/api/v1",
        openzaak_catalogi_api_url="http://openzaak.test/catalogi/api/v1",
        openzaak_client_id="test-client",
        openzaak_secret="test-secret",
        app_url="http://localhost:8000",
        log_level="DEBUG",
        log_format="console",
    )


@pytest.fixture
async def test_engine():
    """Create a test database engine with in-memory SQLite."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # SQLite doesn't support schemas, need to handle this for foreign keys
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def app(test_settings, test_session):
    """Create a test application with overridden dependencies."""
    app = create_app()

    # Override settings
    app.dependency_overrides[get_settings] = lambda: test_settings

    # Override database session - must override get_db which is used by endpoints
    async def get_test_db():
        yield test_session

    app.dependency_overrides[get_db] = get_test_db

    return app


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# Factory fixtures for creating test data


@pytest.fixture
def make_uuid():
    """Factory for creating UUIDs."""

    def _make_uuid() -> uuid.UUID:
        return uuid.uuid4()

    return _make_uuid


@pytest.fixture
def organisation_data(make_uuid):
    """Factory for creating organisation test data."""

    def _organisation_data(**overrides) -> dict:
        data = {
            "uuid": make_uuid(),
            "identifier": f"https://example.org/org/{make_uuid()}",
            "naam": "Test Organisatie",
            "rsin": "123456789",
            "is_actief": True,
        }
        data.update(overrides)
        return data

    return _organisation_data


@pytest.fixture
def category_data(make_uuid):
    """Factory for creating information category test data."""

    def _category_data(**overrides) -> dict:
        data = {
            "uuid": make_uuid(),
            "identifier": f"c_{make_uuid().hex[:8]}",
            "naam": "Test Categorie",
            "naam_meervoud": "Test Categorieën",
            "definitie": "Test definitie",
            "omschrijving": "Test omschrijving",
            "oorsprong": "test",
            "order": 0,
            "bron_bewaartermijn": "",
            "selectiecategorie": "",
            "archiefnominatie": "",
            "bewaartermijn": 0,
            "toelichting_bewaartermijn": "",
        }
        data.update(overrides)
        return data

    return _category_data


@pytest.fixture
async def test_eigenaar(test_session, make_uuid):
    """Create a test OrganisationMember (eigenaar) for publications."""
    from gpp_api.db.models import OrganisationMember

    eigenaar = OrganisationMember(
        identifier=f"test-user-{make_uuid()}",
        naam="Test User",
    )
    test_session.add(eigenaar)
    await test_session.commit()
    await test_session.refresh(eigenaar)
    return eigenaar


@pytest.fixture
async def test_publisher(test_session, make_uuid):
    """Create a test Organisation (publisher) for publications."""
    from gpp_api.db.models import Organisation

    publisher = Organisation(
        uuid=make_uuid(),
        identifier=f"https://example.org/org/{make_uuid()}",
        naam="Test Publisher",
        rsin="123456789",
    )
    test_session.add(publisher)
    await test_session.commit()
    await test_session.refresh(publisher)
    return publisher


@pytest.fixture
def publication_data(make_uuid):
    """Factory for creating publication test data.

    Note: eigenaar_id is required. Pass it via overrides or use test_eigenaar fixture.
    """

    def _publication_data(**overrides) -> dict:
        data = {
            "uuid": make_uuid(),
            "officiele_titel": "Test Publicatie",
            "verkorte_titel": "Test",
            "omschrijving": "Test omschrijving",
            "publicatiestatus": "concept",
            "registratiedatum": datetime.now(timezone.utc),
            "laatst_gewijzigd_datum": datetime.now(timezone.utc),
        }
        data.update(overrides)
        return data

    return _publication_data


@pytest.fixture
def document_data(make_uuid):
    """Factory for creating document test data.

    Note: eigenaar_id is required. Pass it via overrides.
    """

    def _document_data(publicatie_id: int, eigenaar_id: int, **overrides) -> dict:
        data = {
            "uuid": make_uuid(),
            "publicatie_id": publicatie_id,
            "eigenaar_id": eigenaar_id,
            "officiele_titel": "Test Document",
            "verkorte_titel": "Test",
            "omschrijving": "Test omschrijving",
            "publicatiestatus": "concept",
            "creatiedatum": datetime.now(timezone.utc).date(),
            "bestandsnaam": "test.pdf",
            "bestandsformaat": "application/pdf",
            "bestandsomvang": 1024,
            "registratiedatum": datetime.now(timezone.utc),
            "laatst_gewijzigd_datum": datetime.now(timezone.utc),
        }
        data.update(overrides)
        return data

    return _document_data


# Mocked external services


@pytest.fixture
def mock_openzaak():
    """Mock OpenZaak API responses using respx."""
    with respx.mock(assert_all_called=False) as respx_mock:
        # Mock document creation
        respx_mock.post("http://openzaak.test/documenten/api/v1/enkelvoudiginformatieobjecten").mock(
            return_value=Response(
                201,
                json={
                    "url": f"http://openzaak.test/documenten/api/v1/enkelvoudiginformatieobjecten/{uuid.uuid4()}",
                    "identificatie": "DOC-001",
                    "bronorganisatie": "123456789",
                    "creatiedatum": "2024-01-01",
                    "titel": "Test Document",
                    "vertrouwelijkheidaanduiding": "openbaar",
                    "auteur": "GPP",
                    "status": "definitief",
                    "formaat": "application/pdf",
                    "taal": "nld",
                    "bestandsnaam": "test.pdf",
                    "bestandsomvang": 1024,
                    "link": "",
                    "beschrijving": "",
                    "informatieobjecttype": "http://openzaak.test/catalogi/api/v1/informatieobjecttypen/test-uuid",
                    "locked": True,
                    "lock": "test-lock-value",
                    "bestandsdelen": [],
                },
            )
        )

        # Mock document lock
        respx_mock.post(url__regex=r".*/enkelvoudiginformatieobjecten/.*/lock").mock(
            return_value=Response(200, json={"lock": "test-lock"})
        )

        # Mock document unlock
        respx_mock.post(url__regex=r".*/enkelvoudiginformatieobjecten/.*/unlock").mock(
            return_value=Response(204)
        )

        # Mock document patch (file upload)
        respx_mock.patch(url__regex=r".*/enkelvoudiginformatieobjecten/.*").mock(
            return_value=Response(200, json={})
        )

        # Mock document download
        respx_mock.get(url__regex=r".*/enkelvoudiginformatieobjecten/.*/download").mock(
            return_value=Response(200, content=b"PDF content here")
        )

        yield respx_mock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.xadd = AsyncMock(return_value="1234567890-0")
    mock.close = AsyncMock()
    return mock
