"""Tests for event Pydantic schemas."""
import pytest
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError

from app.schemas.event import VenueSchema, EventCreate, EventResponse


@pytest.mark.unit
def test_event_create_schema_validation():
    """Test that EventCreate schema validates correct data."""
    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    venue = VenueSchema(
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Madison Square Garden",
        address_line1="4 Pennsylvania Plaza",
        city="New York",
        state="NY",
        country="USA",
        postal_code="10001",
    )

    event_data = EventCreate(
        title="Tech Conference 2025",
        description="Annual technology conference",
        start_time=start_time,
        end_time=end_time,
        total_tickets=500,
        venue=venue,
    )

    assert event_data.title == "Tech Conference 2025"
    assert event_data.total_tickets == 500
    assert event_data.venue.latitude == 40.7128
    assert event_data.venue.longitude == -74.0060


@pytest.mark.unit
def test_invalid_datetime_range_rejected():
    """Test that EventCreate rejects invalid datetime ranges."""
    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time - timedelta(hours=1)  # End before start

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

    with pytest.raises(ValidationError) as exc_info:
        EventCreate(
            title="Invalid Event",
            start_time=start_time,
            end_time=end_time,
            total_tickets=100,
            venue=venue,
        )

    assert "start_time must be before end_time" in str(exc_info.value)


@pytest.mark.unit
def test_past_start_time_rejected():
    """Test that EventCreate rejects events with start_time in the past."""
    start_time = datetime.now(timezone.utc) - timedelta(days=1)  # Past
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

    with pytest.raises(ValidationError) as exc_info:
        EventCreate(
            title="Past Event",
            start_time=start_time,
            end_time=end_time,
            total_tickets=100,
            venue=venue,
        )

    assert "start_time must be in the future" in str(exc_info.value)


@pytest.mark.unit
def test_negative_ticket_quantity_rejected():
    """Test that negative ticket quantities are rejected."""
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

    with pytest.raises(ValidationError):
        EventCreate(
            title="Invalid Tickets",
            start_time=start_time,
            end_time=end_time,
            total_tickets=-10,  # Negative
            venue=venue,
        )


@pytest.mark.unit
def test_zero_ticket_quantity_rejected():
    """Test that zero ticket quantities are rejected."""
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

    with pytest.raises(ValidationError):
        EventCreate(
            title="No Tickets",
            start_time=start_time,
            end_time=end_time,
            total_tickets=0,  # Zero
            venue=venue,
        )


@pytest.mark.unit
def test_venue_coordinates_validation():
    """Test that venue coordinates are validated."""
    # Valid coordinates
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
    assert venue.latitude == 40.7128
    assert venue.longitude == -74.0060


@pytest.mark.unit
def test_invalid_latitude_rejected():
    """Test that invalid latitude values are rejected."""
    # Latitude out of range (-90 to 90)
    with pytest.raises(ValidationError):
        VenueSchema(
            latitude=100.0,  # Invalid
            longitude=-74.0060,
            venue_name="Venue",
            address_line1="123 St",
            city="NYC",
            state="NY",
            country="USA",
            postal_code="10001",
        )


@pytest.mark.unit
def test_invalid_longitude_rejected():
    """Test that invalid longitude values are rejected."""
    # Longitude out of range (-180 to 180)
    with pytest.raises(ValidationError):
        VenueSchema(
            latitude=40.7128,
            longitude=200.0,  # Invalid
            venue_name="Venue",
            address_line1="123 St",
            city="NYC",
            state="NY",
            country="USA",
            postal_code="10001",
        )


@pytest.mark.unit
def test_timezone_aware_datetime_required():
    """Test that timezone-aware datetime is required."""
    # Naive datetime (no timezone)
    start_time = datetime.now() + timedelta(days=7)  # No timezone
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

    with pytest.raises(ValidationError) as exc_info:
        EventCreate(
            title="Naive Datetime Event",
            start_time=start_time,
            end_time=end_time,
            total_tickets=100,
            venue=venue,
        )

    assert "must be timezone-aware" in str(exc_info.value)


@pytest.mark.unit
def test_venue_required_fields():
    """Test that all required venue fields must be provided."""
    with pytest.raises(ValidationError):
        VenueSchema(
            latitude=40.7128,
            longitude=-74.0060,
            # Missing required fields
        )


@pytest.mark.unit
def test_event_title_not_empty():
    """Test that event title cannot be empty."""
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

    with pytest.raises(ValidationError):
        EventCreate(
            title="",  # Empty string
            start_time=start_time,
            end_time=end_time,
            total_tickets=100,
            venue=venue,
        )


@pytest.mark.unit
def test_optional_description():
    """Test that description is optional."""
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

    event = EventCreate(
        title="Event without description",
        start_time=start_time,
        end_time=end_time,
        total_tickets=100,
        venue=venue,
        # No description
    )

    assert event.description is None


@pytest.mark.unit
def test_optional_address_line2():
    """Test that address_line2 is optional in venue."""
    venue = VenueSchema(
        latitude=40.7128,
        longitude=-74.0060,
        venue_name="Venue",
        address_line1="123 St",
        city="NYC",
        state="NY",
        country="USA",
        postal_code="10001",
        # No address_line2
    )

    assert venue.address_line2 is None
