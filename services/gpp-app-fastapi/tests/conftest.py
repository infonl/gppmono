"""Pytest configuration and fixtures for gpp-app-fastapi tests."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from gpp_app.auth.oidc import OdpcUser, get_current_user
from gpp_app.config import Settings, get_settings
from gpp_app.db.engine import get_session
from gpp_app.db.models import Base
from gpp_app.main import create_app

# Test database URL - in-memory SQLite for fast tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with mocked values."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        gpp_api_base_url="http://gpp-api.test:8000",
        gpp_api_token="test-token",
        woo_hoo_base_url="http://woo-hoo.test:8000",
        woo_hoo_health_timeout_seconds=5,
        woo_hoo_generate_timeout_seconds=30,
        session_secret_key="test-secret-key-minimum-32-characters-long",
        oidc_admin_role="admin",
        app_url="http://localhost:8000",
        log_level="DEBUG",
        log_format="console",
    )


@pytest.fixture
def dev_user() -> OdpcUser:
    """Create a dev mode user for testing."""
    return OdpcUser.dev_user()


@pytest.fixture
def admin_user() -> OdpcUser:
    """Create an admin user for testing."""
    return OdpcUser(
        is_logged_in=True,
        is_admin=True,
        id="admin-user",
        full_name="Admin User",
        email="admin@test.nl",
        roles=["admin"],
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
    def set_sqlite_pragma(dbapi_connection, _connection_record):
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
def app(test_settings, test_session, dev_user):
    """Create a test application with overridden dependencies."""
    app = create_app()

    # Override settings
    app.dependency_overrides[get_settings] = lambda: test_settings

    # Override database session
    async def get_test_session():
        yield test_session

    app.dependency_overrides[get_session] = get_test_session

    # Override auth - use dev user by default
    app.dependency_overrides[get_current_user] = lambda: dev_user

    return app


@pytest.fixture
def app_with_admin(test_settings, test_session, admin_user):
    """Create a test application with admin user."""
    app = create_app()

    app.dependency_overrides[get_settings] = lambda: test_settings

    async def get_test_session():
        yield test_session

    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_current_user] = lambda: admin_user

    return app


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def admin_client(app_with_admin) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with admin user."""
    async with AsyncClient(transport=ASGITransport(app=app_with_admin), base_url="http://test") as ac:
        yield ac


# Mock external services


@pytest.fixture
def mock_gpp_api():
    """Mock gpp-api responses using respx."""
    with respx.mock(assert_all_called=False) as respx_mock:
        # Mock publications list
        respx_mock.get("http://gpp-api.test:8000/api/v2/publicaties").mock(
            return_value=Response(
                200,
                json={
                    "count": 0,
                    "results": [],
                },
            )
        )

        # Mock documents list
        respx_mock.get("http://gpp-api.test:8000/api/v2/documenten").mock(
            return_value=Response(
                200,
                json={
                    "count": 0,
                    "results": [],
                },
            )
        )

        # Mock organisations
        respx_mock.get("http://gpp-api.test:8000/api/v2/organisaties").mock(
            return_value=Response(
                200,
                json={
                    "count": 1,
                    "results": [
                        {
                            "uuid": str(uuid.uuid4()),
                            "identifier": "https://example.org/org/1",
                            "naam": "Test Org",
                            "oorsprong": "test",
                            "rsin": "123456789",
                            "isActief": True,
                        }
                    ],
                },
            )
        )

        # Mock categories
        respx_mock.get("http://gpp-api.test:8000/api/v2/informatiecategorieen").mock(
            return_value=Response(
                200,
                json={
                    "count": 0,
                    "results": [],
                },
            )
        )

        # Mock topics
        respx_mock.get("http://gpp-api.test:8000/api/v2/onderwerpen").mock(
            return_value=Response(
                200,
                json={
                    "count": 0,
                    "results": [],
                },
            )
        )

        yield respx_mock


@pytest.fixture
def _mock_woo_hoo():
    """Mock woo-hoo responses using respx (side-effect fixture)."""
    with respx.mock(assert_all_called=False) as respx_mock:
        # Mock health check
        respx_mock.get("http://woo-hoo.test:8000/health").mock(
            return_value=Response(
                200,
                json={"status": "healthy", "version": "1.0.0"},
            )
        )

        # Mock metadata generation
        respx_mock.post(url__regex=r".*/api/v1/metadata/generate-from-publicatiebank.*").mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "request_id": str(uuid.uuid4()),
                    "suggestion": {
                        "metadata": {
                            "titelcollectie": {
                                "officieleTitel": "Generated Title",
                            },
                            "omschrijvingen": ["Generated description"],
                        }
                    },
                    "error": None,
                },
            )
        )

        yield respx_mock
