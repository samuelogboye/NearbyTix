"""Pydantic schemas for Ticket endpoints."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.ticket import TicketStatus


class TicketReserve(BaseModel):
    """Schema for reserving a ticket."""

    user_id: UUID = Field(..., description="User ID reserving the ticket")
    event_id: UUID = Field(..., description="Event ID to reserve ticket for")

    model_config = {"from_attributes": True}


class UserSummary(BaseModel):
    """Summary of user information in ticket response."""

    id: UUID
    name: str
    email: str

    model_config = {"from_attributes": True}


class EventSummary(BaseModel):
    """Summary of event information in ticket response."""

    id: UUID
    title: str
    start_time: datetime
    end_time: datetime
    venue_name: str
    city: str
    state: str

    model_config = {"from_attributes": True}


class TicketResponse(BaseModel):
    """Schema for ticket response."""

    id: UUID
    user_id: UUID
    event_id: UUID
    status: TicketStatus
    created_at: datetime
    expires_at: Optional[datetime]
    paid_at: Optional[datetime]
    updated_at: datetime

    # Nested relationships
    user: Optional[UserSummary] = None
    event: Optional[EventSummary] = None

    # Computed properties
    is_expired: bool = False
    is_paid: bool = False
    is_reserved: bool = False

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, ticket) -> "TicketResponse":
        """
        Create response from ORM model.

        Args:
            ticket: Ticket ORM model

        Returns:
            TicketResponse object
        """
        user_summary = None
        if ticket.user:
            user_summary = UserSummary(
                id=ticket.user.id,
                name=ticket.user.name,
                email=ticket.user.email,
            )

        event_summary = None
        if ticket.event:
            event_summary = EventSummary(
                id=ticket.event.id,
                title=ticket.event.title,
                start_time=ticket.event.start_time,
                end_time=ticket.event.end_time,
                venue_name=ticket.event.venue_name,
                city=ticket.event.city,
                state=ticket.event.state,
            )

        return cls(
            id=ticket.id,
            user_id=ticket.user_id,
            event_id=ticket.event_id,
            status=ticket.status,
            created_at=ticket.created_at,
            expires_at=ticket.expires_at,
            paid_at=ticket.paid_at,
            updated_at=ticket.updated_at,
            user=user_summary,
            event=event_summary,
            is_expired=ticket.is_expired,
            is_paid=ticket.is_paid,
            is_reserved=ticket.is_reserved,
        )


class TicketListItem(BaseModel):
    """Schema for ticket list item (simplified)."""

    id: UUID
    event_id: UUID
    status: TicketStatus
    created_at: datetime
    expires_at: Optional[datetime]

    # Event info
    event_title: str
    event_start_time: datetime

    model_config = {"from_attributes": True}


class TicketListResponse(BaseModel):
    """Schema for paginated ticket list response."""

    tickets: list[TicketListItem]
    total: int
    skip: int
    limit: int

    model_config = {"from_attributes": True}


class TicketPayment(BaseModel):
    """Schema for marking a ticket as paid."""

    # In a real system, this would include payment details
    # For this assessment, we'll keep it simple
    pass

    model_config = {"from_attributes": True}
