"""Event API endpoints."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.event import EventCreate, EventResponse, EventListResponse
from app.services.event_service import EventService


router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "/",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event",
)
async def create_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    """
    Create a new event.

    Args:
        event_data: Event creation data
        db: Database session

    Returns:
        Created event

    Raises:
        HTTPException: If validation fails
    """
    try:
        service = EventService(db)
        event = await service.create_event(event_data)
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
