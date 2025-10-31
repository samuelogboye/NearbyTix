"""Pytest configuration and fixtures for testing."""
import asyncio
import pytest
import pytest_asyncio
import sqlalchemy as sa
from typing import AsyncGenerator
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient
from geoalchemy2.elements import WKTElement

from app.database import Base
from app.config import settings
from app.models.user import User
from app.models.event import Event
from app.models.ticket import Ticket, TicketStatus
from app.utils.auth import hash_password, create_access_token


# Test database URL (use same credentials, different database)
# Format: postgresql+asyncpg://user:password@host:port/database
TEST_DATABASE_URL = settings.DATABASE_URL.rsplit("/", 1)[0] + "/nearbytix_test"


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


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with database session override."""
    from app.main import app
    from app.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user with location in San Francisco."""
    user = User(
        name="Test User",
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        location=WKTElement("POINT(-122.4194 37.7749)", srid=4326),  # San Francisco
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user2(db_session: AsyncSession) -> User:
    """Create a second test user with location in Los Angeles."""
    user = User(
        name="Test User 2",
        email="test2@example.com",
        hashed_password=hash_password("testpassword456"),
        location=WKTElement("POINT(-118.2437 34.0522)", srid=4326),  # Los Angeles
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user_no_location(db_session: AsyncSession) -> User:
    """Create a test user without location."""
    user = User(
        name="Test User No Location",
        email="nolocation@example.com",
        hashed_password=hash_password("testpassword789"),
        location=None,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user: User) -> str:
    """Create an authentication token for test user."""
    return create_access_token(data={"sub": str(test_user.id), "email": test_user.email})


@pytest.fixture
def auth_token2(test_user2: User) -> str:
    """Create an authentication token for second test user."""
    return create_access_token(data={"sub": str(test_user2.id), "email": test_user2.email})


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """Create authorization headers with Bearer token for test user."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def auth_headers2(auth_token2: str) -> dict:
    """Create authorization headers for second test user."""
    return {"Authorization": f"Bearer {auth_token2}"}


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def test_event(db_session: AsyncSession, test_user: User) -> Event:
    """Create a test event in San Francisco."""
    event = Event(
        creator_id=test_user.id,
        title="Test Event",
        description="A test event",
        start_time=datetime.now(timezone.utc) + timedelta(days=7),
        end_time=datetime.now(timezone.utc) + timedelta(days=7, hours=2),
        location=WKTElement("POINT(-122.4194 37.7749)", srid=4326),  # San Francisco
        venue_name="Test Venue",
        address_line1="123 Test St",
        address_line2="Suite 100",
        city="San Francisco",
        state="CA",
        country="USA",
        postal_code="94102",
        total_tickets=100,
        tickets_sold=0,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def test_event_nearby(db_session: AsyncSession, test_user: User) -> Event:
    """Create a nearby test event (~1km from San Francisco center)."""
    event = Event(
        creator_id=test_user.id,
        title="Nearby Event",
        description="An event nearby",
        start_time=datetime.now(timezone.utc) + timedelta(days=14),
        end_time=datetime.now(timezone.utc) + timedelta(days=14, hours=3),
        location=WKTElement("POINT(-122.4094 37.7849)", srid=4326),  # ~1km from SF
        venue_name="Nearby Venue",
        address_line1="456 Close St",
        city="San Francisco",
        state="CA",
        country="USA",
        postal_code="94103",
        total_tickets=50,
        tickets_sold=0,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def test_event_sold_out(db_session: AsyncSession, test_user: User) -> Event:
    """Create a sold out test event."""
    event = Event(
        creator_id=test_user.id,
        title="Sold Out Event",
        description="A sold out event",
        start_time=datetime.now(timezone.utc) + timedelta(days=10),
        end_time=datetime.now(timezone.utc) + timedelta(days=10, hours=2),
        location=WKTElement("POINT(-122.4194 37.7749)", srid=4326),
        venue_name="Test Venue",
        address_line1="123 Test St",
        city="San Francisco",
        state="CA",
        country="USA",
        postal_code="94102",
        total_tickets=10,
        tickets_sold=10,  # Sold out
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def test_ticket(db_session: AsyncSession, test_user: User, test_event: Event) -> Ticket:
    """Create a reserved test ticket."""
    ticket = Ticket(
        user_id=test_user.id,
        event_id=test_event.id,
        status=TicketStatus.RESERVED,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=2),
    )
    db_session.add(ticket)

    # Update event tickets_sold
    test_event.tickets_sold += 1

    await db_session.commit()
    await db_session.refresh(ticket)
    return ticket


@pytest_asyncio.fixture
async def test_ticket_paid(db_session: AsyncSession, test_user: User, test_event: Event) -> Ticket:
    """Create a paid test ticket."""
    ticket = Ticket(
        user_id=test_user.id,
        event_id=test_event.id,
        status=TicketStatus.PAID,
        paid_at=datetime.now(timezone.utc),
    )
    db_session.add(ticket)

    # Update event tickets_sold
    test_event.tickets_sold += 1

    await db_session.commit()
    await db_session.refresh(ticket)
    return ticket
