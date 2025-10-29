"""Event model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, Text, DateTime, Index, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography

from app.database import Base

if TYPE_CHECKING:
    from app.models.ticket import Ticket
    from app.models.user import User


class Event(Base):
    """Event model for storing event information."""

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # Event creator
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Event details
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Event timing
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Venue - Composite of location (geospatial) and address fields
    # Location stored as Geography(POINT) with SRID 4326
    location = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False,
        index=True,
    )

    # Address components
    venue_name: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)

    # Ticket inventory
    total_tickets: Mapped[int] = mapped_column(Integer, nullable=False)
    tickets_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[creator_id],
    )

    tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        back_populates="event",
        cascade="all, delete-orphan",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("total_tickets > 0", name="check_total_tickets_positive"),
        CheckConstraint("tickets_sold >= 0", name="check_tickets_sold_non_negative"),
        CheckConstraint(
            "tickets_sold <= total_tickets", name="check_tickets_sold_not_exceed_total"
        ),
        CheckConstraint("start_time < end_time", name="check_valid_time_range"),
        # Spatial index on location for efficient geospatial queries
        Index("idx_event_location", "location", postgresql_using="gist"),
    )

    @property
    def tickets_available(self) -> int:
        """Calculate available tickets."""
        return self.total_tickets - self.tickets_sold

    @property
    def is_sold_out(self) -> bool:
        """Check if event is sold out."""
        return self.tickets_sold >= self.total_tickets

    @property
    def is_upcoming(self) -> bool:
        """Check if event is in the future."""
        return self.start_time > datetime.utcnow()

    @property
    def is_ongoing(self) -> bool:
        """Check if event is currently happening."""
        now = datetime.utcnow()
        return self.start_time <= now <= self.end_time

    @property
    def has_ended(self) -> bool:
        """Check if event has ended."""
        return self.end_time < datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"<Event(id={self.id}, title={self.title}, "
            f"tickets={self.tickets_sold}/{self.total_tickets})>"
        )
