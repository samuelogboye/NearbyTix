"""Celery tasks for ticket management."""
import asyncio
from datetime import datetime, timezone
from uuid import UUID
from typing import List

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.celery_app import celery_app
from app.config import settings
from app.models.ticket import Ticket, TicketStatus
from app.models.event import Event


def create_async_db_session():
    """
    Create a fresh async engine and session for Celery tasks.

    This is necessary because Celery tasks run in forked worker processes
    and use asyncio.run() which creates new event loops. We need to create
    the engine within the event loop to avoid connection pool issues.
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
        poolclass=None,  # Disable pooling for Celery tasks to avoid event loop conflicts
    )

    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    return engine, session_maker


@celery_app.task(name="app.tasks.ticket_tasks.expire_ticket_task", bind=True, max_retries=3)
def expire_ticket_task(self, ticket_id: str):
    """
    Expire a single ticket (delayed task).

    This task is scheduled when a ticket is reserved and runs after
    the expiration time (default: 2 minutes).

    Args:
        ticket_id: UUID of the ticket to expire (as string)
    """
    try:
        # Run async function in sync context
        return asyncio.run(_expire_ticket_async(ticket_id))
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60)


async def _expire_ticket_async(ticket_id: str):
    """
    Async function to expire a ticket.

    Args:
        ticket_id: UUID of the ticket (as string)

    Returns:
        dict with status and message
    """
    # Create fresh engine and session within this event loop
    engine, session_maker = create_async_db_session()

    try:
        async with session_maker() as db:
            try:
                ticket_uuid = UUID(ticket_id)

                # Get ticket with lock
                result = await db.execute(
                    select(Ticket).where(Ticket.id == ticket_uuid).with_for_update()
                )
                ticket = result.scalar_one_or_none()

                if not ticket:
                    return {"status": "not_found", "message": f"Ticket {ticket_id} not found"}

                # Only expire if still reserved
                if ticket.status != TicketStatus.RESERVED:
                    return {
                        "status": "skipped",
                        "message": f"Ticket {ticket_id} is {ticket.status}, not reserved",
                    }

                # Check if actually expired
                if ticket.expires_at and datetime.now(timezone.utc) < ticket.expires_at:
                    return {
                        "status": "not_yet_expired",
                        "message": f"Ticket {ticket_id} not yet expired",
                    }

                # Get event and decrement tickets_sold
                result = await db.execute(
                    select(Event).where(Event.id == ticket.event_id).with_for_update()
                )
                event = result.scalar_one_or_none()

                if event:
                    event.tickets_sold = max(0, event.tickets_sold - 1)

                # Update ticket status
                ticket.status = TicketStatus.EXPIRED

                await db.commit()

                return {
                    "status": "expired",
                    "message": f"Ticket {ticket_id} expired successfully",
                    "event_id": str(ticket.event_id),
                }

            except Exception as e:
                await db.rollback()
                raise e
    finally:
        # Always dispose of the engine to clean up connections
        await engine.dispose()


@celery_app.task(name="app.tasks.ticket_tasks.cleanup_expired_tickets")
def cleanup_expired_tickets():
    """
    Periodic task to clean up expired tickets (safety net).

    This runs every minute via Celery Beat and expires any tickets
    that should have been expired but weren't (e.g., if the delayed
    task failed or was missed).

    Returns:
        dict with count of expired tickets
    """
    return asyncio.run(_cleanup_expired_tickets_async())


async def _cleanup_expired_tickets_async():
    """
    Async function to cleanup expired tickets.

    Returns:
        dict with status and count
    """
    # Create fresh engine and session within this event loop
    engine, session_maker = create_async_db_session()

    try:
        async with session_maker() as db:
            try:
                now = datetime.now(timezone.utc)

                # Find all reserved tickets that should be expired
                result = await db.execute(
                    select(Ticket)
                    .where(Ticket.status == TicketStatus.RESERVED)
                    .where(Ticket.expires_at != None)
                    .where(Ticket.expires_at < now)
                    .limit(100)  # Process in batches
                )
                expired_tickets: List[Ticket] = list(result.scalars().all())

                if not expired_tickets:
                    return {"status": "success", "expired_count": 0}

                # Group tickets by event for efficient updates
                event_ids = set(ticket.event_id for ticket in expired_tickets)

                # Lock and update each event's ticket count
                for event_id in event_ids:
                    result = await db.execute(
                        select(Event).where(Event.id == event_id).with_for_update()
                    )
                    event = result.scalar_one_or_none()

                    if event:
                        # Count how many tickets for this event are being expired
                        tickets_to_expire = len(
                            [t for t in expired_tickets if t.event_id == event_id]
                        )
                        event.tickets_sold = max(0, event.tickets_sold - tickets_to_expire)

                # Update all ticket statuses
                for ticket in expired_tickets:
                    ticket.status = TicketStatus.EXPIRED

                await db.commit()

                return {
                    "status": "success",
                    "expired_count": len(expired_tickets),
                    "event_count": len(event_ids),
                }

            except Exception as e:
                await db.rollback()
                raise e
    finally:
        # Always dispose of the engine to clean up connections
        await engine.dispose()


@celery_app.task(name="app.tasks.ticket_tasks.cancel_expiration_task")
def cancel_expiration_task(task_id: str):
    """
    Cancel a scheduled expiration task.

    This is called when a ticket is paid for before it expires.

    Args:
        task_id: Celery task ID to cancel
    """
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return {"status": "cancelled", "task_id": task_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}
