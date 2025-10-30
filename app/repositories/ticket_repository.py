"""Ticket repository for database operations."""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.ticket import Ticket, TicketStatus


class TicketRepository:
    """Repository for Ticket model database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db

    async def create(
        self,
        user_id: UUID,
        event_id: UUID,
        status: TicketStatus = TicketStatus.RESERVED,
        expires_at: Optional[datetime] = None,
        expiration_task_id: Optional[str] = None,
    ) -> Ticket:
        """
        Create a new ticket.

        Args:
            user_id: User UUID
            event_id: Event UUID
            status: Ticket status (default: RESERVED)
            expires_at: Expiration timestamp (optional)
            expiration_task_id: Celery task ID for expiration (optional)

        Returns:
            Created Ticket object
        """
        ticket = Ticket(
            user_id=user_id,
            event_id=event_id,
            status=status,
            expires_at=expires_at,
            expiration_task_id=expiration_task_id,
        )

        self.db.add(ticket)
        await self.db.flush()
        await self.db.refresh(ticket)
        return ticket

    async def get_by_id(
        self, ticket_id: UUID, with_relations: bool = False
    ) -> Optional[Ticket]:
        """
        Get ticket by ID.

        Args:
            ticket_id: Ticket UUID
            with_relations: If True, eagerly load user and event relationships

        Returns:
            Ticket object or None if not found
        """
        query = select(Ticket).where(Ticket.id == ticket_id)

        if with_relations:
            query = query.options(joinedload(Ticket.user), joinedload(Ticket.event))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, ticket_id: UUID) -> Optional[Ticket]:
        """
        Get ticket by ID with row lock (SELECT FOR UPDATE).
        Used to prevent race conditions during status updates.

        Args:
            ticket_id: Ticket UUID

        Returns:
            Ticket object or None if not found
        """
        result = await self.db.execute(
            select(Ticket).where(Ticket.id == ticket_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[TicketStatus] = None,
    ) -> List[Ticket]:
        """
        Get all tickets for a user.

        Args:
            user_id: User UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status (optional)

        Returns:
            List of Ticket objects
        """
        query = (
            select(Ticket)
            .where(Ticket.user_id == user_id)
            .order_by(Ticket.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        if status is not None:
            query = query.where(Ticket.status == status)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_event(
        self,
        event_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[TicketStatus] = None,
    ) -> List[Ticket]:
        """
        Get all tickets for an event.

        Args:
            event_id: Event UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status (optional)

        Returns:
            List of Ticket objects
        """
        query = (
            select(Ticket)
            .where(Ticket.event_id == event_id)
            .order_by(Ticket.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        if status is not None:
            query = query.where(Ticket.status == status)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_status(
        self,
        ticket_id: UUID,
        new_status: TicketStatus,
        paid_at: Optional[datetime] = None,
    ) -> Optional[Ticket]:
        """
        Update ticket status.

        Args:
            ticket_id: Ticket UUID
            new_status: New ticket status
            paid_at: Payment timestamp (optional, for PAID status)

        Returns:
            Updated Ticket object or None if not found
        """
        # Use SELECT FOR UPDATE to prevent race conditions
        ticket = await self.get_by_id_for_update(ticket_id)
        if not ticket:
            return None

        ticket.status = new_status
        if paid_at is not None:
            ticket.paid_at = paid_at

        await self.db.flush()
        await self.db.refresh(ticket)
        return ticket

    async def get_expired_tickets(self, limit: int = 100) -> List[Ticket]:
        """
        Get tickets that have expired (reserved tickets past expires_at time).

        Args:
            limit: Maximum number of tickets to return

        Returns:
            List of expired Ticket objects
        """
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Ticket)
            .where(Ticket.status == TicketStatus.RESERVED)
            .where(Ticket.expires_at != None)
            .where(Ticket.expires_at < now)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete(self, ticket_id: UUID) -> bool:
        """
        Delete a ticket.

        Args:
            ticket_id: Ticket UUID

        Returns:
            True if deleted, False if not found
        """
        ticket = await self.get_by_id(ticket_id)
        if not ticket:
            return False

        await self.db.delete(ticket)
        await self.db.flush()
        return True
