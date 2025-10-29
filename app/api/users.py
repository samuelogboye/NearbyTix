"""User API endpoints."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, LocationUpdate
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Create a new user.

    Args:
        user_data: User creation data
        db: Database session

    Returns:
        Created user

    Raises:
        HTTPException: If validation fails or user already exists
    """
    try:
        service = UserService(db)
        user = await service.create_user(user_data)
        return user
    except Exception as e:
        # Check if it's a unique constraint violation (email already exists)
        if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email {user_data.email} already exists",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
)
async def get_user(
    user_id: UUID = Path(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get user details by ID.

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        User details

    Raises:
        HTTPException 404: If user not found
    """
    try:
        service = UserService(db)
        user = await service.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
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
    "/{user_id}/location",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user location",
)
async def update_user_location(
    location_data: LocationUpdate,
    user_id: UUID = Path(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update user location.

    Args:
        user_id: User UUID
        location_data: New location data
        db: Database session

    Returns:
        Updated user

    Raises:
        HTTPException 404: If user not found
    """
    try:
        service = UserService(db)
        user = await service.update_user_location(user_id, location_data)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )

        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user location: {str(e)}",
        )
