"""Ticket model."""
import uuid
import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.event import Event


class TicketStatus(str, enum.Enum):
    """Enum for ticket status."""

    RESERVED = "reserved"
    PAID = "paid"
    EXPIRED = "expired"


class Ticket(Base):
    """Ticket model for storing ticket reservations and purchases."""

    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Ticket status
    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(TicketStatus, name="ticket_status", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        default=TicketStatus.RESERVED,
        nullable=False,
        index=True,
    )

    # Celery task ID for expiration task (optional, for cancellation)
    expiration_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tickets")
    event: Mapped["Event"] = relationship("Event", back_populates="tickets")

    # Indexes for efficient queries
    __table_args__ = (
        # Composite index for finding user's tickets for a specific event
        Index("idx_ticket_user_event", "user_id", "event_id"),
        # Index for finding expired tickets that need cleanup
        Index(
            "idx_ticket_status_expires_at",
            "status",
            "expires_at",
            postgresql_where="status = 'reserved' AND expires_at IS NOT NULL",
        ),
    )

    @property
    def is_expired(self) -> bool:
        """Check if ticket has expired."""
        if self.status != TicketStatus.RESERVED or not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_paid(self) -> bool:
        """Check if ticket is paid."""
        return self.status == TicketStatus.PAID

    @property
    def is_reserved(self) -> bool:
        """Check if ticket is reserved."""
        return self.status == TicketStatus.RESERVED

    def __repr__(self) -> str:
        return (
            f"<Ticket(id={self.id}, user_id={self.user_id}, "
            f"event_id={self.event_id}, status={self.status})>"
        )
