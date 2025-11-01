"""Tests for database models."""
import pytest
from datetime import datetime, timedelta, timezone
from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.models import User, Event, Ticket, TicketStatus
from app.utils.auth import hash_password


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_model_creation(db_session):
    """Test creating a User model instance."""
    user = User(
        name="John Doe",
        email="john@example.com",
        hashed_password=hash_password("testpassword"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.name == "John Doe"
    assert user.email == "john@example.com"
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_email_uniqueness(db_session):
    """Test that user email must be unique."""
    user1 = User(name="John Doe", email="john@example.com", hashed_password=hash_password("test"))
    db_session.add(user1)
    await db_session.commit()

    user2 = User(name="Jane Doe", email="john@example.com", hashed_password=hash_password("test"))
    db_session.add(user2)

    with pytest.raises(Exception):  # IntegrityError for duplicate email
        await db_session.commit()

    # Rollback the session after the expected error
    await db_session.rollback()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_user_with_location(db_session):
    """Test creating a user with geospatial location."""
    # WKT format: POINT(longitude latitude)
    location = WKTElement("POINT(-73.935242 40.730610)", srid=4326)

    user = User(
        name="John Doe",
        email="john@example.com",
        hashed_password=hash_password("testpassword"),
        location=location,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.location is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_event_model_with_venue(db_session):
    """Test creating an Event model with venue information."""
    # Create user first (required for creator_id)
    user = User(
        name="Event Creator",
        email="creator@example.com",
        hashed_password=hash_password("testpassword"),
    )
    db_session.add(user)
    await db_session.commit()

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)
    location = WKTElement("POINT(-73.935242 40.730610)", srid=4326)

    event = Event(
        creator_id=user.id,
        title="Tech Conference 2025",
        description="Annual tech conference",
        start_time=start_time,
        end_time=end_time,
        location=location,
        venue_name="Convention Center",
        address_line1="123 Main St",
        city="New York",
        state="NY",
        country="USA",
        postal_code="10001",
        total_tickets=1000,
        tickets_sold=0,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    assert event.id is not None
    assert event.title == "Tech Conference 2025"
    assert event.location is not None
    assert event.venue_name == "Convention Center"
    assert event.total_tickets == 1000
    assert event.tickets_sold == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_event_location_geospatial_type(db_session):
    """Test that event location is properly stored as geospatial type."""
    # Create user first (required for creator_id)
    user = User(
        name="Event Creator",
        email="creator2@example.com",
        hashed_password=hash_password("testpassword"),
    )
    db_session.add(user)
    await db_session.commit()

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)
    location = WKTElement("POINT(-118.243683 34.052235)", srid=4326)  # LA coordinates

    event = Event(
        creator_id=user.id,
        title="LA Event",
        start_time=start_time,
        end_time=end_time,
        location=location,
        venue_name="LA Venue",
        address_line1="456 Sunset Blvd",
        city="Los Angeles",
        state="CA",
        country="USA",
        postal_code="90028",
        total_tickets=500,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    assert event.location is not None
    # The location should be stored and retrievable


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ticket_model_with_relationships(db_session):
    """Test Ticket model with relationships to User and Event."""
    # Create user
    user = User(name="John Doe", email="john@example.com", hashed_password=hash_password("testpassword"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)  # Refresh to get ID

    # Create event
    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)
    location = WKTElement("POINT(-73.935242 40.730610)", srid=4326)

    event = Event(
        creator_id=user.id,
        title="Concert",
        start_time=start_time,
        end_time=end_time,
        location=location,
        venue_name="Madison Square Garden",
        address_line1="4 Pennsylvania Plaza",
        city="New York",
        state="NY",
        country="USA",
        postal_code="10001",
        total_tickets=100,
    )
    db_session.add(event)
    await db_session.commit()

    # Create ticket
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=2)
    ticket = Ticket(
        user_id=user.id,
        event_id=event.id,
        status=TicketStatus.RESERVED,
        expires_at=expires_at,
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)

    assert ticket.id is not None
    assert ticket.user_id == user.id
    assert ticket.event_id == event.id
    assert ticket.user is not None
    assert ticket.event is not None
    assert ticket.user.email == "john@example.com"
    assert ticket.event.title == "Concert"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ticket_status_enum_values(db_session):
    """Test that ticket status enum has correct values."""
    assert TicketStatus.RESERVED == "reserved"
    assert TicketStatus.PAID == "paid"
    assert TicketStatus.EXPIRED == "expired"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ticket_default_status_is_reserved(db_session):
    """Test that ticket default status is RESERVED."""
    user = User(name="John Doe", email="john@example.com", hashed_password=hash_password("testpassword"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)  # Refresh to get ID

    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)
    location = WKTElement("POINT(-73.935242 40.730610)", srid=4326)

    event = Event(
        creator_id=user.id,
        title="Concert",
        start_time=start_time,
        end_time=end_time,
        location=location,
        venue_name="Venue",
        address_line1="123 St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
        total_tickets=100,
    )
    db_session.add(event)
    await db_session.commit()

    ticket = Ticket(
        user_id=user.id,
        event_id=event.id,
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)

    assert ticket.status == TicketStatus.RESERVED


@pytest.mark.unit
def test_event_tickets_available_property():
    """Test event tickets_available property."""
    event = Event(
        title="Test Event",
        total_tickets=100,
        tickets_sold=30,
    )
    assert event.tickets_available == 70


@pytest.mark.unit
def test_event_is_sold_out_property():
    """Test event is_sold_out property."""
    event_not_sold_out = Event(
        title="Test Event",
        total_tickets=100,
        tickets_sold=50,
    )
    assert event_not_sold_out.is_sold_out is False

    event_sold_out = Event(
        title="Sold Out Event",
        total_tickets=100,
        tickets_sold=100,
    )
    assert event_sold_out.is_sold_out is True


@pytest.mark.unit
def test_ticket_is_expired_property():
    """Test ticket is_expired property."""
    past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    future_time = datetime.now(timezone.utc) + timedelta(minutes=5)

    expired_ticket = Ticket(
        status=TicketStatus.RESERVED,
        expires_at=past_time,
    )
    assert expired_ticket.is_expired is True

    valid_ticket = Ticket(
        status=TicketStatus.RESERVED,
        expires_at=future_time,
    )
    assert valid_ticket.is_expired is False

    paid_ticket = Ticket(
        status=TicketStatus.PAID,
        expires_at=past_time,
    )
    assert paid_ticket.is_expired is False


@pytest.mark.unit
def test_ticket_status_properties():
    """Test ticket status check properties."""
    reserved_ticket = Ticket(status=TicketStatus.RESERVED)
    assert reserved_ticket.is_reserved is True
    assert reserved_ticket.is_paid is False

    paid_ticket = Ticket(status=TicketStatus.PAID)
    assert paid_ticket.is_paid is True
    assert paid_ticket.is_reserved is False
