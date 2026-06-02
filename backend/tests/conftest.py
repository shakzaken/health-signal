"""
Shared fixtures for the backend test suite.

Uses an in-memory SQLite database so tests run without PostgreSQL.
The ai-agent HTTP call is mocked at the httpx level.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base  # registers all models via its bottom-level imports

# SQLite in-memory — fast, no external dependency needed for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


async def create_test_tables(engine: AsyncEngine) -> None:
    """Create all tables against the given engine. Used only in tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_test_tables(engine: AsyncEngine) -> None:
    """Drop all tables. Used only in tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session")
def test_engine():
    return create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )


@pytest.fixture
async def db_session(test_engine):
    """Create all tables fresh for each test, yield a session, then drop everything."""
    await create_test_tables(test_engine)

    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session

    await drop_test_tables(test_engine)


@pytest.fixture
def client(db_session, mocker):
    """TestClient with the DB session overridden to use in-memory SQLite."""
    from db.session import get_session
    from main import app

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
