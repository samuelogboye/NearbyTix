"""User model."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography

from app.database import Base

if TYPE_CHECKING:
    from app.models.ticket import Ticket


class User(Base):
    """User model for storing user information."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Geospatial field for user location
    # Stored as Geography(POINT) with SRID 4326 (WGS84 - standard GPS coordinates)
    location = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=True,
    )

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
    tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"
