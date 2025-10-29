"""Ticket service layer for business logic."""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.ticket_repository import TicketRepository
from app.repositories.event_repository import EventRepository
from app.repositories.user_repository import UserRepository
from app.schemas.ticket import TicketReserve, TicketResponse, TicketListItem, TicketListResponse
from app.models.ticket import Ticket, TicketStatus
from app.models.event import Event
from app.config import settings

# Import Celery tasks
try:
    from app.tasks.ticket_tasks import expire_ticket_task, cancel_expiration_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False


class TicketNotFoundException(Exception):
    """Exception raised when ticket is not found."""

    pass


class EventNotFoundException(Exception):
    """Exception raised when event is not found."""

    pass


class UserNotFoundException(Exception):
    """Exception raised when user is not found."""

    pass


class EventSoldOutException(Exception):
    """Exception raised when event is sold out."""

    pass


class TicketExpiredException(Exception):
    """Exception raised when attempting to pay for an expired ticket."""

    pass


class InvalidStatusTransitionException(Exception):
    """Exception raised when attempting an invalid status transition."""

    pass


class TicketService:
    """Service layer for ticket business logic."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db
        self.ticket_repo = TicketRepository(db)
        self.event_repo = EventRepository(db)
        self.user_repo = UserRepository(db)

    async def reserve_ticket(self, user_id: UUID, reservation_data: TicketReserve) -> TicketResponse:
        """
        Reserve a ticket for a user.

        This method implements atomic ticket reservation with database locking
        to prevent overselling (race conditions).

        Flow:
        1. Lock event row (SELECT FOR UPDATE)
        2. Check event exists
        3. Check user exists
        4. Check tickets available (tickets_sold < total_tickets)
        5. Create ticket with status="reserved" and expiration time
        6. Increment event.tickets_sold atomically
        7. Commit transaction
        8. Schedule Celery expiration task (future implementation)

        Args:
            user_id: User UUID (from authenticated user)
            reservation_data: Ticket reservation data

        Returns:
            Created ticket response

        Raises:
            EventNotFoundException: If event doesn't exist
            UserNotFoundException: If user doesn't exist
            EventSoldOutException: If no tickets available
        """
        # Step 1: Get and lock event row (SELECT FOR UPDATE)
        # This prevents other concurrent reservations from reading stale data
        result = await self.db.execute(
            select(Event)
            .where(Event.id == reservation_data.event_id)
            .with_for_update()
        )
        event = result.scalar_one_or_none()

        # Step 2: Check event exists
        if not event:
            raise EventNotFoundException(
                f"Event with ID {reservation_data.event_id} not found"
            )

        # Step 3: Check user exists
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(
                f"User with ID {user_id} not found"
            )

        # Step 4: Check tickets available
        if event.tickets_sold >= event.total_tickets:
            raise EventSoldOutException(
                f"Event '{event.title}' is sold out ({event.tickets_sold}/{event.total_tickets} tickets sold)"
            )

        # Step 5: Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(seconds=settings.TICKET_EXPIRATION_TIME)

        # Step 6: Create ticket with reserved status
        ticket = await self.ticket_repo.create(
            user_id=user_id,
            event_id=reservation_data.event_id,
            status=TicketStatus.RESERVED,
            expires_at=expires_at,
        )

        # Step 7: Increment tickets_sold atomically
        # This happens in the same transaction as ticket creation
        event.tickets_sold += 1

        # Step 8: Commit transaction
        await self.db.commit()

        # Refresh to get latest data
        await self.db.refresh(ticket)
        await self.db.refresh(event)

        # Load relationships for response
        await self.db.refresh(ticket, ["user", "event"])

        # Step 8: Schedule Celery expiration task
        if CELERY_AVAILABLE:
            task = expire_ticket_task.apply_async(
                args=[str(ticket.id)],
                countdown=settings.TICKET_EXPIRATION_TIME
            )
            ticket.expiration_task_id = task.id
            await self.db.commit()

        return TicketResponse.from_orm_model(ticket)

    async def mark_ticket_paid(self, ticket_id: UUID) -> TicketResponse:
        """
        Mark a ticket as paid.

        This validates that:
        - Ticket exists
        - Ticket is in "reserved" status
        - Ticket has not expired

        Args:
            ticket_id: Ticket UUID

        Returns:
            Updated ticket response

        Raises:
            TicketNotFoundException: If ticket doesn't exist
            InvalidStatusTransitionException: If ticket is not reserved
            TicketExpiredException: If ticket has expired
        """
        # Get ticket with row lock
        ticket = await self.ticket_repo.get_by_id_for_update(ticket_id)

        if not ticket:
            raise TicketNotFoundException(f"Ticket with ID {ticket_id} not found")

        # Check current status
        if ticket.status != TicketStatus.RESERVED:
            raise InvalidStatusTransitionException(
                f"Cannot pay for ticket with status '{ticket.status}'. "
                f"Only 'reserved' tickets can be paid for."
            )

        # Check expiration
        if ticket.is_expired:
            raise TicketExpiredException(
                f"Ticket has expired at {ticket.expires_at}. Cannot process payment."
            )

        # Update status to paid
        paid_at = datetime.utcnow()
        ticket = await self.ticket_repo.update_status(
            ticket_id=ticket_id,
            new_status=TicketStatus.PAID,
            paid_at=paid_at,
        )

        await self.db.commit()

        # Cancel Celery expiration task
        if CELERY_AVAILABLE and ticket.expiration_task_id:
            cancel_expiration_task.delay(ticket.expiration_task_id)

        # Reload relationships
        await self.db.refresh(ticket, ["user", "event"])

        return TicketResponse.from_orm_model(ticket)

    async def get_ticket_by_id(self, ticket_id: UUID) -> Optional[TicketResponse]:
        """
        Get ticket by ID.

        Args:
            ticket_id: Ticket UUID

        Returns:
            Ticket response or None if not found
        """
        ticket = await self.ticket_repo.get_by_id(ticket_id, with_relations=True)
        if not ticket:
            return None

        return TicketResponse.from_orm_model(ticket)

    async def get_user_tickets(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[TicketStatus] = None,
    ) -> TicketListResponse:
        """
        Get all tickets for a user.

        Args:
            user_id: User UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status (optional)

        Returns:
            Paginated list of tickets
        """
        tickets = await self.ticket_repo.get_by_user(
            user_id=user_id,
            skip=skip,
            limit=limit,
            status=status,
        )

        # Load event relationships for each ticket
        for ticket in tickets:
            await self.db.refresh(ticket, ["event"])

        ticket_items = [
            TicketListItem(
                id=ticket.id,
                event_id=ticket.event_id,
                status=ticket.status,
                created_at=ticket.created_at,
                expires_at=ticket.expires_at,
                event_title=ticket.event.title,
                event_start_time=ticket.event.start_time,
            )
            for ticket in tickets
        ]

        # Count total (simplified - in production, use a count query)
        total = len(tickets)

        return TicketListResponse(
            tickets=ticket_items,
            total=total,
            skip=skip,
            limit=limit,
        )
