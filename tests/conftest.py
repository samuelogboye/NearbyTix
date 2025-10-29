"""Pytest configuration and fixtures for testing."""
import asyncio
import pytest
import pytest_asyncio
import sqlalchemy as sa
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.database import Base
from app.config import settings
from app.models import User, Event, Ticket  # noqa: F401 - imported for metadata


# Test database URL (use a separate test database)
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/nearbytix", "/nearbytix_test")


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    # Create session factory
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db(test_engine):
    """Clean up database after each test."""
    yield

    # Truncate all tables after each test
    async with test_engine.begin() as conn:
        await conn.execute(sa.text("TRUNCATE TABLE tickets CASCADE"))
        await conn.execute(sa.text("TRUNCATE TABLE events CASCADE"))
        await conn.execute(sa.text("TRUNCATE TABLE users CASCADE"))


@pytest.fixture
def anyio_backend():
    """Use asyncio as the async backend."""
    return "asyncio"


@pytest.fixture
def client(db_session):
    """Create a test client with database session override."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
