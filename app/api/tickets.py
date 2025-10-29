"""Ticket API endpoints."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.ticket import (
    TicketReserve,
    TicketResponse,
    TicketListResponse,
    TicketPayment,
)
from app.services.ticket_service import (
    TicketService,
    TicketNotFoundException,
    EventNotFoundException,
    UserNotFoundException,
    EventSoldOutException,
    TicketExpiredException,
    InvalidStatusTransitionException,
)
from app.models.ticket import TicketStatus


router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post(
    "/",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve a ticket",
    description="Reserve a ticket for a user at an event. Ticket expires in 2 minutes if not paid.",
)
async def reserve_ticket(
    reservation_data: TicketReserve,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """
    Reserve a ticket for a user.

    This endpoint implements atomic reservation with database locking to prevent overselling.

    Args:
        reservation_data: Reservation data (user_id, event_id)
        db: Database session

    Returns:
        Created ticket

    Raises:
        HTTPException 404: If event or user not found
        HTTPException 409: If event is sold out
    """
    try:
        service = TicketService(db)
        ticket = await service.reserve_ticket(reservation_data)
        return ticket
    except EventNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except UserNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except EventSoldOutException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reserve ticket: {str(e)}",
        )


@router.post(
    "/{ticket_id}/pay",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark ticket as paid",
    description="Mark a reserved ticket as paid. Cannot pay for expired tickets.",
)
async def pay_for_ticket(
    ticket_id: UUID = Path(..., description="Ticket ID"),
    payment_data: TicketPayment = None,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """
    Mark a ticket as paid.

    Args:
        ticket_id: Ticket UUID
        payment_data: Payment information (currently unused)
        db: Database session

    Returns:
        Updated ticket

    Raises:
        HTTPException 404: If ticket not found
        HTTPException 409: If ticket is not reserved or invalid status
        HTTPException 410: If ticket has expired
    """
    try:
        service = TicketService(db)
        ticket = await service.mark_ticket_paid(ticket_id)
        return ticket
    except TicketNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InvalidStatusTransitionException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except TicketExpiredException as e:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process payment: {str(e)}",
        )


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Get ticket by ID",
)
async def get_ticket(
    ticket_id: UUID = Path(..., description="Ticket ID"),
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """
    Get ticket details by ID.

    Args:
        ticket_id: Ticket UUID
        db: Database session

    Returns:
        Ticket details

    Raises:
        HTTPException 404: If ticket not found
    """
    try:
        service = TicketService(db)
        ticket = await service.get_ticket_by_id(ticket_id)

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket with ID {ticket_id} not found",
            )

        return ticket
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve ticket: {str(e)}",
        )


@router.get(
    "/user/{user_id}",
    response_model=TicketListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user's ticket history",
    description="Get all tickets for a specific user with optional status filter.",
)
async def get_user_tickets(
    user_id: UUID = Path(..., description="User ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    status: Optional[TicketStatus] = Query(None, description="Filter by ticket status"),
    db: AsyncSession = Depends(get_db),
) -> TicketListResponse:
    """
    Get all tickets for a user.

    Args:
        user_id: User UUID
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        status: Filter by ticket status (optional)
        db: Database session

    Returns:
        Paginated list of tickets
    """
    try:
        service = TicketService(db)
        tickets = await service.get_user_tickets(
            user_id=user_id,
            skip=skip,
            limit=limit,
            status=status,
        )
        return tickets
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tickets: {str(e)}",
        )
