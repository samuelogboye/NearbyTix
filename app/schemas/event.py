"""Pydantic schemas for Event endpoints."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self


class VenueSchema(BaseModel):
    """Schema for event venue information."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    venue_name: str = Field(..., min_length=1, max_length=255)
    address_line1: str = Field(..., min_length=1, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)

    @field_validator("latitude", "longitude")
    @classmethod
    def validate_coordinates(cls, v: float, info) -> float:
        """Validate that coordinates are valid numbers."""
        if not isinstance(v, (int, float)):
            raise ValueError(f"{info.field_name} must be a number")
        return v

    model_config = {"from_attributes": True}


class EventCreate(BaseModel):
    """Schema for creating a new event."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    start_time: datetime = Field(..., description="Event start time (UTC)")
    end_time: datetime = Field(..., description="Event end time (UTC)")
    total_tickets: int = Field(..., gt=0, description="Total number of tickets available")
    venue: VenueSchema

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_timezone_aware(cls, v: datetime, info) -> datetime:
        """Ensure datetime is timezone-aware."""
        if v.tzinfo is None:
            raise ValueError(f"{info.field_name} must be timezone-aware")
        return v

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        """Validate that start_time is before end_time."""
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self

    @model_validator(mode="after")
    def validate_future_event(self) -> Self:
        """Validate that event is in the future."""
        now = datetime.now(self.start_time.tzinfo)
        if self.start_time <= now:
            raise ValueError("start_time must be in the future")
        return self

    model_config = {"from_attributes": True}


class EventResponse(BaseModel):
    """Schema for event response."""

    id: UUID
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    total_tickets: int
    tickets_sold: int
    tickets_available: int
    is_sold_out: bool

    # Venue information
    latitude: float
    longitude: float
    venue_name: str
    address_line1: str
    address_line2: Optional[str]
    city: str
    state: str
    country: str
    postal_code: str

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, event) -> "EventResponse":
        """Create response from ORM model."""
        # Extract lat/lng from geography location
        # The location is stored as a WKB element, we'll handle this in the service layer
        return cls(
            id=event.id,
            title=event.title,
            description=event.description,
            start_time=event.start_time,
            end_time=event.end_time,
            total_tickets=event.total_tickets,
            tickets_sold=event.tickets_sold,
            tickets_available=event.tickets_available,
            is_sold_out=event.is_sold_out,
            latitude=0.0,  # Will be populated from location
            longitude=0.0,  # Will be populated from location
            venue_name=event.venue_name,
            address_line1=event.address_line1,
            address_line2=event.address_line2,
            city=event.city,
            state=event.state,
            country=event.country,
            postal_code=event.postal_code,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )


class EventListItem(BaseModel):
    """Schema for event list item (simplified)."""

    id: UUID
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    tickets_available: int
    is_sold_out: bool
    venue_name: str
    city: str
    state: str

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    """Schema for paginated event list response."""

    events: list[EventListItem]
    total: int
    skip: int
    limit: int

    model_config = {"from_attributes": True}


class EventUpdate(BaseModel):
    """Schema for updating an event."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_tickets: Optional[int] = Field(None, gt=0)

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_timezone_aware(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Ensure datetime is timezone-aware if provided."""
        if v is not None and v.tzinfo is None:
            raise ValueError(f"{info.field_name} must be timezone-aware")
        return v

    model_config = {"from_attributes": True}
