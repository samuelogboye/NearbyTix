"""Event service layer for business logic."""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, cast
import geoalchemy2
from geoalchemy2 import functions as geo_func

from app.repositories.event_repository import EventRepository
from app.schemas.event import EventCreate, EventResponse, EventListItem, EventListResponse, EventUpdate
from app.models.event import Event


class EventService:
    """Service layer for event business logic."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db
        self.repository = EventRepository(db)

    async def create_event(self, creator_id: UUID, event_data: EventCreate) -> EventResponse:
        """
        Create a new event.

        Args:
            creator_id: User ID of the event creator
            event_data: Event creation data

        Returns:
            Created event response

        Raises:
            ValueError: If validation fails
        """
        # Ensure times are in UTC
        start_time_utc = event_data.start_time
        end_time_utc = event_data.end_time

        # Create event
        event = await self.repository.create(
            creator_id=creator_id,
            title=event_data.title,
            description=event_data.description,
            start_time=start_time_utc,
            end_time=end_time_utc,
            total_tickets=event_data.total_tickets,
            latitude=event_data.venue.latitude,
            longitude=event_data.venue.longitude,
            venue_name=event_data.venue.venue_name,
            address_line1=event_data.venue.address_line1,
            address_line2=event_data.venue.address_line2,
            city=event_data.venue.city,
            state=event_data.venue.state,
            country=event_data.venue.country,
            postal_code=event_data.venue.postal_code,
        )

        await self.db.commit()
        return await self._event_to_response(event, event_data.venue.latitude, event_data.venue.longitude)

    async def get_event_by_id(self, event_id: UUID) -> Optional[EventResponse]:
        """
        Get event by ID.

        Args:
            event_id: Event UUID

        Returns:
            Event response or None if not found
        """
        event = await self.repository.get_by_id(event_id)
        if not event:
            return None

        # Extract lat/lng from location
        lat, lng = await self._extract_coordinates(event)
        return await self._event_to_response(event, lat, lng)

    async def get_all_events(
        self, skip: int = 0, limit: int = 100, upcoming_only: bool = False
    ) -> EventListResponse:
        """
        Get all events with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            upcoming_only: If True, only return future events

        Returns:
            Paginated list of events
        """
        events = await self.repository.get_all(skip=skip, limit=limit, upcoming_only=upcoming_only)
        total = await self.repository.count_all(upcoming_only=upcoming_only)

        event_items = [
            EventListItem(
                id=event.id,
                title=event.title,
                description=event.description,
                start_time=event.start_time,
                end_time=event.end_time,
                tickets_available=event.tickets_available,
                is_sold_out=event.is_sold_out,
                venue_name=event.venue_name,
                city=event.city,
                state=event.state,
            )
            for event in events
        ]

        return EventListResponse(events=event_items, total=total, skip=skip, limit=limit)

    async def _extract_coordinates(self, event: Event) -> tuple[float, float]:
        """
        Extract latitude and longitude from event location.

        Args:
            event: Event object

        Returns:
            Tuple of (latitude, longitude)
        """
        if event.location is None:
            return (0.0, 0.0)

        # Query to extract coordinates from geography type
        # Cast Geography to Geometry to use ST_Y and ST_X functions
        result = await self.db.execute(
            select(
                geo_func.ST_Y(cast(event.location, geoalchemy2.Geometry)).label("lat"),
                geo_func.ST_X(cast(event.location, geoalchemy2.Geometry)).label("lng"),
            )
        )
        coords = result.first()

        if coords:
            return (float(coords.lat), float(coords.lng))
        return (0.0, 0.0)

    async def update_event(self, event_id: UUID, event_data: EventUpdate) -> Optional[EventResponse]:
        """
        Update an event.

        Args:
            event_id: Event UUID
            event_data: Event update data

        Returns:
            Updated event response or None if not found
        """
        # Get the event first
        event = await self.repository.get_by_id(event_id)
        if not event:
            return None

        # Prepare update data
        update_dict = event_data.model_dump(exclude_unset=True)

        # Handle venue updates
        if 'venue' in update_dict and update_dict['venue']:
            venue_data = update_dict.pop('venue')
            if 'latitude' in venue_data and 'longitude' in venue_data:
                from geoalchemy2.elements import WKTElement
                update_dict['location'] = WKTElement(
                    f"POINT({venue_data['longitude']} {venue_data['latitude']})",
                    srid=4326
                )
            # Add other venue fields
            for key in ['venue_name', 'address_line1', 'address_line2', 'city', 'state', 'country', 'postal_code']:
                if key in venue_data:
                    update_dict[key] = venue_data[key]

        # Update event
        updated_event = await self.repository.update(event_id, **update_dict)
        if not updated_event:
            return None

        await self.db.commit()

        # Extract coordinates and return response
        lat, lng = await self._extract_coordinates(updated_event)
        return await self._event_to_response(updated_event, lat, lng)

    async def delete_event(self, event_id: UUID) -> bool:
        """
        Delete an event.

        Args:
            event_id: Event UUID

        Returns:
            True if deleted, False if not found
        """
        result = await self.repository.delete(event_id)
        if result:
            await self.db.commit()
        return result

    async def _event_to_response(
        self, event: Event, latitude: float, longitude: float
    ) -> EventResponse:
        """
        Convert Event model to EventResponse.

        Args:
            event: Event model
            latitude: Venue latitude
            longitude: Venue longitude

        Returns:
            EventResponse object
        """
        return EventResponse(
            id=event.id,
            creator_id=event.creator_id,
            title=event.title,
            description=event.description,
            start_time=event.start_time,
            end_time=event.end_time,
            total_tickets=event.total_tickets,
            tickets_sold=event.tickets_sold,
            tickets_available=event.tickets_available,
            is_sold_out=event.is_sold_out,
            latitude=latitude,
            longitude=longitude,
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
