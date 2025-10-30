"""Event repository for database operations."""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement

from app.models.event import Event


class EventRepository:
    """Repository for Event model database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db

    async def create(
        self,
        creator_id: UUID,
        title: str,
        start_time,
        end_time,
        total_tickets: int,
        latitude: float,
        longitude: float,
        venue_name: str,
        address_line1: str,
        city: str,
        state: str,
        country: str,
        postal_code: str,
        description: Optional[str] = None,
        address_line2: Optional[str] = None,
    ) -> Event:
        """
        Create a new event.

        Args:
            creator_id: User ID of the event creator
            title: Event title
            start_time: Event start time
            end_time: Event end time
            total_tickets: Total number of tickets
            latitude: Venue latitude
            longitude: Venue longitude
            venue_name: Venue name
            address_line1: Address line 1
            city: City
            state: State
            country: Country
            postal_code: Postal code
            description: Event description (optional)
            address_line2: Address line 2 (optional)

        Returns:
            Created Event object
        """
        # Create WKT Point from coordinates (longitude, latitude order for WKT)
        location = WKTElement(f"POINT({longitude} {latitude})", srid=4326)

        event = Event(
            creator_id=creator_id,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
            venue_name=venue_name,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            total_tickets=total_tickets,
            tickets_sold=0,
        )

        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def get_by_id(self, event_id: UUID) -> Optional[Event]:
        """
        Get event by ID.

        Args:
            event_id: Event UUID

        Returns:
            Event object or None if not found
        """
        result = await self.db.execute(select(Event).where(Event.id == event_id))
        return result.scalar_one_or_none()

    async def get_all(
        self, skip: int = 0, limit: int = 100, upcoming_only: bool = False
    ) -> List[Event]:
        """
        Get all events with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            upcoming_only: If True, only return future events

        Returns:
            List of Event objects
        """
        query = select(Event).order_by(Event.start_time.asc()).offset(skip).limit(limit)

        if upcoming_only:
            from datetime import datetime

            query = query.where(Event.start_time > datetime.now(timezone.utc))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_all(self, upcoming_only: bool = False) -> int:
        """
        Count total number of events.

        Args:
            upcoming_only: If True, only count future events

        Returns:
            Total count of events
        """
        query = select(func.count(Event.id))

        if upcoming_only:
            from datetime import datetime

            query = query.where(Event.start_time > datetime.now(timezone.utc))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def update(self, event_id: UUID, **kwargs) -> Optional[Event]:
        """
        Update an event.

        Args:
            event_id: Event UUID
            **kwargs: Fields to update

        Returns:
            Updated Event object or None if not found
        """
        event = await self.get_by_id(event_id)
        if not event:
            return None

        for key, value in kwargs.items():
            if hasattr(event, key) and value is not None:
                setattr(event, key, value)

        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def delete(self, event_id: UUID) -> bool:
        """
        Delete an event.

        Args:
            event_id: Event UUID

        Returns:
            True if deleted, False if not found
        """
        event = await self.get_by_id(event_id)
        if not event:
            return False

        await self.db.delete(event)
        await self.db.flush()
        return True

    async def increment_tickets_sold(self, event_id: UUID, amount: int = 1) -> bool:
        """
        Increment tickets_sold counter atomically.

        Args:
            event_id: Event UUID
            amount: Amount to increment by (default: 1)

        Returns:
            True if successful, False if event not found
        """
        event = await self.get_by_id(event_id)
        if not event:
            return False

        event.tickets_sold += amount
        await self.db.flush()
        return True

    async def decrement_tickets_sold(self, event_id: UUID, amount: int = 1) -> bool:
        """
        Decrement tickets_sold counter atomically.

        Args:
            event_id: Event UUID
            amount: Amount to decrement by (default: 1)

        Returns:
            True if successful, False if event not found
        """
        event = await self.get_by_id(event_id)
        if not event:
            return False

        # Ensure we don't go below 0
        event.tickets_sold = max(0, event.tickets_sold - amount)
        await self.db.flush()
        return True
