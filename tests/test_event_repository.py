"""Tests for event repository."""
import pytest
from datetime import datetime, timedelta, timezone

from app.repositories.event_repository import EventRepository
from app.models.event import Event


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_event_returns_event(db_session):
    """Test that create() returns an event with ID."""
    repository = EventRepository(db_session)

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    event = await repository.create(
        title="Test Event",
        description="Test Description",
        start_time=start_time,
        end_time=end_time,
        total_tickets=100,
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Test Venue",
        address_line1="123 Test St",
        city="New York",
        state="NY",
        country="USA",
        postal_code="10001",
    )

    assert event.id is not None
    assert event.title == "Test Event"
    assert event.total_tickets == 100
    assert event.tickets_sold == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_event_by_id_found(db_session):
    """Test getting an event by ID when it exists."""
    repository = EventRepository(db_session)

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    created_event = await repository.create(
        title="Test Event",
        start_time=start_time,
        end_time=end_time,
        total_tickets=100,
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Test Venue",
        address_line1="123 Test St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
    )
    await db_session.commit()

    found_event = await repository.get_by_id(created_event.id)

    assert found_event is not None
    assert found_event.id == created_event.id
    assert found_event.title == "Test Event"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_event_by_id_not_found(db_session):
    """Test getting an event by ID when it doesn't exist."""
    repository = EventRepository(db_session)

    from uuid import uuid4

    non_existent_id = uuid4()
    found_event = await repository.get_by_id(non_existent_id)

    assert found_event is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_events_with_pagination(db_session):
    """Test getting all events with pagination."""
    repository = EventRepository(db_session)

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    # Create 5 events
    for i in range(5):
        await repository.create(
            title=f"Event {i}",
            start_time=start_time + timedelta(days=i),
            end_time=end_time + timedelta(days=i),
            total_tickets=100,
            latitude=40.7128,
            longitude=-74.0060,
            venue_name="Venue",
            address_line1="123 St",
            city="NYC",
            state="NY",
            country="USA",
            postal_code="10001",
        )
    await db_session.commit()

    # Get first 3 events
    events = await repository.get_all(skip=0, limit=3)
    assert len(events) == 3

    # Get next 2 events
    events = await repository.get_all(skip=3, limit=3)
    assert len(events) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_events_empty_database(db_session):
    """Test getting all events from empty database."""
    repository = EventRepository(db_session)

    events = await repository.get_all()
    assert len(events) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_all_events_upcoming_only(db_session):
    """Test getting only upcoming events."""
    repository = EventRepository(db_session)

    # Create past event
    past_start = datetime.now(timezone.utc) - timedelta(days=7)
    past_end = past_start + timedelta(hours=3)
    await repository.create(
        title="Past Event",
        start_time=past_start,
        end_time=past_end,
        total_tickets=100,
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Venue",
        address_line1="123 St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
    )

    # Create future event
    future_start = datetime.now(timezone.utc) + timedelta(days=7)
    future_end = future_start + timedelta(hours=3)
    await repository.create(
        title="Future Event",
        start_time=future_start,
        end_time=future_end,
        total_tickets=100,
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Venue",
        address_line1="123 St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
    )
    await db_session.commit()

    # Get only upcoming events
    events = await repository.get_all(upcoming_only=True)
    assert len(events) == 1
    assert events[0].title == "Future Event"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_count_all_events(db_session):
    """Test counting all events."""
    repository = EventRepository(db_session)

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    # Create 3 events
    for i in range(3):
        await repository.create(
            title=f"Event {i}",
            start_time=start_time,
            end_time=end_time,
            total_tickets=100,
            latitude=40.7128,
            longitude=-74.0060,
            venue_name="Venue",
            address_line1="123 St",
            city="NYC",
            state="NY",
            country="USA",
            postal_code="10001",
        )
    await db_session.commit()

    count = await repository.count_all()
    assert count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_increment_tickets_sold(db_session):
    """Test incrementing tickets_sold counter."""
    repository = EventRepository(db_session)

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    event = await repository.create(
        title="Test Event",
        start_time=start_time,
        end_time=end_time,
        total_tickets=100,
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Venue",
        address_line1="123 St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
    )
    await db_session.commit()

    assert event.tickets_sold == 0

    # Increment by 1
    await repository.increment_tickets_sold(event.id)
    await db_session.commit()
    await db_session.refresh(event)
    assert event.tickets_sold == 1

    # Increment by 5
    await repository.increment_tickets_sold(event.id, amount=5)
    await db_session.commit()
    await db_session.refresh(event)
    assert event.tickets_sold == 6


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decrement_tickets_sold(db_session):
    """Test decrementing tickets_sold counter."""
    repository = EventRepository(db_session)

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    event = await repository.create(
        title="Test Event",
        start_time=start_time,
        end_time=end_time,
        total_tickets=100,
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Venue",
        address_line1="123 St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
    )
    event.tickets_sold = 10
    await db_session.commit()

    # Decrement by 1
    await repository.decrement_tickets_sold(event.id)
    await db_session.commit()
    await db_session.refresh(event)
    assert event.tickets_sold == 9

    # Decrement by 5
    await repository.decrement_tickets_sold(event.id, amount=5)
    await db_session.commit()
    await db_session.refresh(event)
    assert event.tickets_sold == 4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decrement_tickets_sold_does_not_go_negative(db_session):
    """Test that tickets_sold doesn't go below 0."""
    repository = EventRepository(db_session)

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    event = await repository.create(
        title="Test Event",
        start_time=start_time,
        end_time=end_time,
        total_tickets=100,
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Venue",
        address_line1="123 St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
    )
    event.tickets_sold = 2
    await db_session.commit()

    # Try to decrement by more than available
    await repository.decrement_tickets_sold(event.id, amount=10)
    await db_session.commit()
    await db_session.refresh(event)

    # Should be 0, not negative
    assert event.tickets_sold == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_event(db_session):
    """Test deleting an event."""
    repository = EventRepository(db_session)

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    event = await repository.create(
        title="Test Event",
        start_time=start_time,
        end_time=end_time,
        total_tickets=100,
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Venue",
        address_line1="123 St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
    )
    await db_session.commit()

    event_id = event.id

    # Delete event
    result = await repository.delete(event_id)
    await db_session.commit()
    assert result is True

    # Verify it's deleted
    found_event = await repository.get_by_id(event_id)
    assert found_event is None
