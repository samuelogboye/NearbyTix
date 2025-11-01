"""Tests for ticket Pydantic schemas."""
import pytest
from uuid import uuid4

from app.schemas.ticket import TicketReserve
from app.models.ticket import TicketStatus


@pytest.mark.unit
def test_ticket_reserve_schema_validation():
    """Test that TicketReserve schema validates correct data."""
    event_id = uuid4()

    reservation = TicketReserve(
        event_id=event_id,
    )

    assert reservation.event_id == event_id


@pytest.mark.unit
def test_ticket_status_enum_values():
    """Test that TicketStatus enum has correct values."""
    assert TicketStatus.RESERVED == "reserved"
    assert TicketStatus.PAID == "paid"
    assert TicketStatus.EXPIRED == "expired"
