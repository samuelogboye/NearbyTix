"""User API endpoints."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, LocationUpdate
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Get the profile of the authenticated user.",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get current user profile.

    Args:
        current_user: Authenticated user (from JWT)
        db: Database session

    Returns:
        User profile

    Raises:
        HTTPException 401: If not authenticated
    """
    try:
        service = UserService(db)
        user = await service.get_user_by_id(current_user.id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user: {str(e)}",
        )


@router.put(
    "/me/location",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update my location",
    description="Update the location of the authenticated user.",
)
async def update_my_location(
    location_data: LocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update current user's location.

    Args:
        location_data: New location data
        current_user: Authenticated user (from JWT)
        db: Database session

    Returns:
        Updated user profile

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 404: If user not found
    """
    try:
        service = UserService(db)
        user = await service.update_user_location(current_user.id, location_data)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user location: {str(e)}",
        )
