"""Tests for event service layer."""
import pytest
from datetime import datetime, timedelta, timezone

from app.services.event_service import EventService
from app.schemas.event import EventCreate, VenueSchema


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_event_with_valid_data(db_session):
    """Test creating an event with valid data."""
    service = EventService(db_session)

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    venue = VenueSchema(
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Test Venue",
        address_line1="123 Test St",
        city="New York",
        state="NY",
        country="USA",
        postal_code="10001",
    )

    event_data = EventCreate(
        title="Tech Conference",
        description="Annual conference",
        start_time=start_time,
        end_time=end_time,
        total_tickets=500,
        venue=venue,
    )

    result = await service.create_event(event_data)

    assert result.id is not None
    assert result.title == "Tech Conference"
    assert result.total_tickets == 500
    assert result.tickets_sold == 0
    assert result.tickets_available == 500
    assert result.is_sold_out is False
    assert result.latitude == 40.7128
    assert result.longitude == -74.0060


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_event_by_id_success(db_session):
    """Test getting an event by ID."""
    service = EventService(db_session)

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    venue = VenueSchema(
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Test Venue",
        address_line1="123 Test St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
    )

    event_data = EventCreate(
        title="Test Event",
        start_time=start_time,
        end_time=end_time,
        total_tickets=100,
        venue=venue,
    )

    created = await service.create_event(event_data)
    retrieved = await service.get_event_by_id(created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.title == "Test Event"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_event_by_id_not_found(db_session):
    """Test getting a non-existent event returns None."""
    service = EventService(db_session)

    from uuid import uuid4

    result = await service.get_event_by_id(uuid4())
    assert result is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_all_events_returns_list(db_session):
    """Test getting all events returns paginated list."""
    service = EventService(db_session)

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    venue = VenueSchema(
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Venue",
        address_line1="123 St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
    )

    # Create 3 events
    for i in range(3):
        event_data = EventCreate(
            title=f"Event {i}",
            start_time=start_time + timedelta(days=i),
            end_time=end_time + timedelta(days=i),
            total_tickets=100,
            venue=venue,
        )
        await service.create_event(event_data)

    result = await service.get_all_events(skip=0, limit=10)

    assert result.total == 3
    assert len(result.events) == 3
    assert result.skip == 0
    assert result.limit == 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_all_events_pagination(db_session):
    """Test pagination works correctly."""
    service = EventService(db_session)

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    venue = VenueSchema(
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Venue",
        address_line1="123 St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
    )

    # Create 5 events
    for i in range(5):
        event_data = EventCreate(
            title=f"Event {i}",
            start_time=start_time + timedelta(days=i),
            end_time=end_time + timedelta(days=i),
            total_tickets=100,
            venue=venue,
        )
        await service.create_event(event_data)

    # Get first page
    page1 = await service.get_all_events(skip=0, limit=2)
    assert len(page1.events) == 2
    assert page1.total == 5

    # Get second page
    page2 = await service.get_all_events(skip=2, limit=2)
    assert len(page2.events) == 2

    # Get third page
    page3 = await service.get_all_events(skip=4, limit=2)
    assert len(page3.events) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_upcoming_events_only(db_session):
    """Test filtering for upcoming events only."""
    service = EventService(db_session)

    venue = VenueSchema(
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Venue",
        address_line1="123 St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
    )

    # Create past event
    past_start = datetime.now(timezone.utc) - timedelta(days=7)
    past_end = past_start + timedelta(hours=3)
    past_event = EventCreate(
        title="Past Event",
        start_time=past_start,
        end_time=past_end,
        total_tickets=100,
        venue=venue,
    )
    await service.create_event(past_event)

    # Create future event
    future_start = datetime.now(timezone.utc) + timedelta(days=7)
    future_end = future_start + timedelta(hours=3)
    future_event = EventCreate(
        title="Future Event",
        start_time=future_start,
        end_time=future_end,
        total_tickets=100,
        venue=venue,
    )
    await service.create_event(future_event)

    # Get all events (should include both)
    all_events = await service.get_all_events(upcoming_only=False)
    assert all_events.total == 2

    # Get upcoming only (should only include future event)
    upcoming_events = await service.get_all_events(upcoming_only=True)
    assert upcoming_events.total == 1
    assert upcoming_events.events[0].title == "Future Event"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_timezone_handling(db_session):
    """Test that timezone-aware datetimes are stored correctly."""
    service = EventService(db_session)

    # Use UTC timezone explicitly
    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    venue = VenueSchema(
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Venue",
        address_line1="123 St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
    )

    event_data = EventCreate(
        title="Timezone Test",
        start_time=start_time,
        end_time=end_time,
        total_tickets=100,
        venue=venue,
    )

    result = await service.create_event(event_data)

    # Verify timezone info is preserved
    assert result.start_time.tzinfo is not None
    assert result.end_time.tzinfo is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_list_item_has_required_fields(db_session):
    """Test that event list items contain required fields."""
    service = EventService(db_session)

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    venue = VenueSchema(
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Test Venue",
        address_line1="123 St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
    )

    event_data = EventCreate(
        title="Test Event",
        description="Test Description",
        start_time=start_time,
        end_time=end_time,
        total_tickets=100,
        venue=venue,
    )

    await service.create_event(event_data)

    result = await service.get_all_events()

    assert len(result.events) == 1
    event_item = result.events[0]

    assert event_item.id is not None
    assert event_item.title == "Test Event"
    assert event_item.description == "Test Description"
    assert event_item.venue_name == "Test Venue"
    assert event_item.city == "NYC"
    assert event_item.state == "NY"
    assert event_item.tickets_available == 100
    assert event_item.is_sold_out is False
