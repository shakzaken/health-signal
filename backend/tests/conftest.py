"""
Shared fixtures for the backend test suite.

Uses an in-memory SQLite database so tests run without PostgreSQL.
The ai-agent HTTP call is mocked at the httpx level.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Import all models so SQLModel.metadata knows about all tables
import models.document  # noqa: F401
import models.lab_result  # noqa: F401
import models.symptom  # noqa: F401
import models.supplement  # noqa: F401
import models.timeline  # noqa: F401

# SQLite in-memory — fast, no external dependency needed for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    return create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )


@pytest.fixture
async def db_session(test_engine):
    """Create all tables fresh for each test, yield a session, then drop everything."""
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture
def client(db_session, mocker):
    """
    TestClient with:
    - DB session overridden to use in-memory SQLite
    - create_db_and_tables patched to a no-op (tables already created above)
    """
    from db.session import get_session
    from main import app

    # Skip the real DB table creation in lifespan
    mocker.patch("main.create_db_and_tables", return_value=None)

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
