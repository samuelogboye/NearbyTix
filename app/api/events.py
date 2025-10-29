"""Event API endpoints."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.event import EventCreate, EventResponse, EventListResponse, EventUpdate
from app.services.event_service import EventService


router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "/",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event",
    description="Create a new event. Requires authentication. The authenticated user becomes the event creator.",
)
async def create_event(
    event_data: EventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    """
    Create a new event.

    Args:
        event_data: Event creation data
        current_user: Authenticated user (from JWT)
        db: Database session

    Returns:
        Created event

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 422: If validation fails
    """
    try:
        service = EventService(db)
        event = await service.create_event(current_user.id, event_data)
        return event
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}",
        )


@router.get(
    "/",
    response_model=EventListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all events",
)
async def list_events(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    upcoming_only: bool = Query(False, description="Only return upcoming events"),
    db: AsyncSession = Depends(get_db),
) -> EventListResponse:
    """
    Get a paginated list of events.

    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        upcoming_only: If True, only return future events
        db: Database session

    Returns:
        Paginated list of events
    """
    try:
        service = EventService(db)
        events = await service.get_all_events(skip=skip, limit=limit, upcoming_only=upcoming_only)
        return events
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve events: {str(e)}",
        )


@router.get(
    "/{event_id}",
    response_model=EventResponse,
    status_code=status.HTTP_200_OK,
    summary="Get event by ID",
)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    """
    Get a single event by ID.

    Args:
        event_id: Event UUID
        db: Database session

    Returns:
        Event details

    Raises:
        HTTPException: If event not found
    """
    try:
        service = EventService(db)
        event = await service.get_event_by_id(event_id)

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {event_id} not found",
            )

        return event
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve event: {str(e)}",
        )


@router.put(
    "/{event_id}",
    response_model=EventResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an event",
    description="Update an event. Only the event creator can update it.",
)
async def update_event(
    event_id: UUID = Path(..., description="Event ID"),
    event_data: EventUpdate = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    """
    Update an event.

    Args:
        event_id: Event UUID
        event_data: Event update data
        current_user: Authenticated user (from JWT)
        db: Database session

    Returns:
        Updated event

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If user is not the event creator
        HTTPException 404: If event not found
    """
    try:
        service = EventService(db)

        # Check if event exists and user is the creator
        event = await service.get_event_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {event_id} not found",
            )

        # Check authorization - only creator can update
        if event.creator_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the event creator can update this event",
            )

        # Update the event
        updated_event = await service.update_event(event_id, event_data)
        if not updated_event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {event_id} not found",
            )

        return updated_event
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update event: {str(e)}",
        )


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an event",
    description="Delete an event. Only the event creator can delete it.",
)
async def delete_event(
    event_id: UUID = Path(..., description="Event ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an event.

    Args:
        event_id: Event UUID
        current_user: Authenticated user (from JWT)
        db: Database session

    Returns:
        No content (204)

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If user is not the event creator
        HTTPException 404: If event not found
    """
    try:
        service = EventService(db)

        # Check if event exists and user is the creator
        event = await service.get_event_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {event_id} not found",
            )

        # Check authorization - only creator can delete
        if event.creator_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the event creator can delete this event",
            )

        # Delete the event
        success = await service.delete_event(event_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {event_id} not found",
            )

        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete event: {str(e)}",
        )
