"""User repository for database operations."""
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, cast
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement
import geoalchemy2
from geoalchemy2 import functions as geo_func

from app.models.user import User
from app.schemas.user import UserResponse


class UserRepository:
    """Repository for User model database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db

    async def create(
        self,
        name: str,
        email: str,
        hashed_password: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> User:
        """
        Create a new user.

        Args:
            name: User name
            email: User email
            hashed_password: Hashed password
            latitude: User latitude (optional)
            longitude: User longitude (optional)

        Returns:
            Created User object
        """
        location = None
        if latitude is not None and longitude is not None:
            # Create WKT Point from coordinates
            location = WKTElement(f"POINT({longitude} {latitude})", srid=4326)

        user = User(
            name=name,
            email=email,
            hashed_password=hashed_password,
            location=location,
        )

        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User object or None if not found
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User object or None if not found
        """
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get all users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of User objects
        """
        result = await self.db.execute(
            select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def update(
        self,
        user_id: UUID,
        name: Optional[str] = None,
        email: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Optional[User]:
        """
        Update a user.

        Args:
            user_id: User UUID
            name: New name (optional)
            email: New email (optional)
            latitude: New latitude (optional)
            longitude: New longitude (optional)

        Returns:
            Updated User object or None if not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        if name is not None:
            user.name = name
        if email is not None:
            user.email = email

        # Update location if both lat and lng are provided
        if latitude is not None and longitude is not None:
            location = WKTElement(f"POINT({longitude} {latitude})", srid=4326)
            user.location = location

        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user_id: UUID) -> bool:
        """
        Delete a user.

        Args:
            user_id: User UUID

        Returns:
            True if deleted, False if not found
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False

        await self.db.delete(user)
        await self.db.flush()
        return True

    async def to_response(self, user: User) -> UserResponse:
        """
        Convert User model to UserResponse schema.

        Args:
            user: User model

        Returns:
            UserResponse schema
        """
        latitude = None
        longitude = None

        if user.location:
            # Extract coordinates from Geography Point
            # Cast Geography to Geometry to use ST_Y and ST_X functions
            coords_result = await self.db.execute(
                select(
                    geo_func.ST_Y(cast(user.location, geoalchemy2.Geometry)).label("lat"),
                    geo_func.ST_X(cast(user.location, geoalchemy2.Geometry)).label("lng"),
                )
            )
            coords = coords_result.first()
            if coords:
                latitude = float(coords.lat)
                longitude = float(coords.lng)

        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            latitude=latitude,
            longitude=longitude,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
