"""User service layer for business logic."""
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2 import functions as geo_func
from sqlalchemy import select

from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserResponse, LocationUpdate
from app.models.user import User


class UserService:
    """Service layer for user business logic."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db
        self.repository = UserRepository(db)

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """
        Create a new user.

        Args:
            user_data: User creation data

        Returns:
            Created user response
        """
        user = await self.repository.create(
            name=user_data.name,
            email=user_data.email,
            latitude=user_data.latitude,
            longitude=user_data.longitude,
        )

        await self.db.commit()
        return await self._user_to_response(user)

    async def get_user_by_id(self, user_id: UUID) -> Optional[UserResponse]:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User response or None if not found
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            return None

        return await self._user_to_response(user)

    async def update_user_location(
        self, user_id: UUID, location_data: LocationUpdate
    ) -> Optional[UserResponse]:
        """
        Update user location.

        Args:
            user_id: User UUID
            location_data: New location data

        Returns:
            Updated user response or None if not found
        """
        user = await self.repository.update(
            user_id=user_id,
            latitude=location_data.latitude,
            longitude=location_data.longitude,
        )

        if not user:
            return None

        await self.db.commit()
        return await self._user_to_response(user)

    async def _extract_coordinates(self, user: User) -> tuple[Optional[float], Optional[float]]:
        """
        Extract latitude and longitude from user location.

        Args:
            user: User object

        Returns:
            Tuple of (latitude, longitude) or (None, None)
        """
        if user.location is None:
            return (None, None)

        # Query to extract coordinates from geography type
        result = await self.db.execute(
            select(
                geo_func.ST_Y(geo_func.ST_GeomFromWKB(user.location.data)).label("lat"),
                geo_func.ST_X(geo_func.ST_GeomFromWKB(user.location.data)).label("lng"),
            )
        )
        coords = result.first()

        if coords:
            return (float(coords.lat), float(coords.lng))
        return (None, None)

    async def _user_to_response(self, user: User) -> UserResponse:
        """
        Convert User model to UserResponse.

        Args:
            user: User model

        Returns:
            UserResponse object
        """
        lat, lng = await self._extract_coordinates(user)

        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            latitude=lat,
            longitude=lng,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
