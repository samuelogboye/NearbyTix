"""Recommendations API endpoints."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, cast

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.geospatial_service import GeospatialService
from app.schemas.recommendation import EventRecommendation, RecommendationsResponse
from app.repositories.user_repository import UserRepository
import geoalchemy2
from geoalchemy2 import functions as geo_func


router = APIRouter(prefix="/for-you", tags=["recommendations"])


@router.get(
    "/",
    response_model=RecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get personalized event recommendations",
    description="Get event recommendations based on authenticated user's location using geospatial queries.",
)
async def get_recommendations(
    radius: Optional[float] = Query(
        None,
        ge=1,
        le=500,
        description="Search radius in kilometers (default: 50km)",
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecommendationsResponse:
    """
    Get personalized event recommendations for the authenticated user.

    This endpoint uses PostGIS geospatial queries to find events near the user's location.

    Args:
        radius: Search radius in kilometers (optional, default from settings)
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        current_user: Authenticated user (from JWT)
        db: Database session

    Returns:
        List of recommended events with distances

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 400: If user has no location set
    """
    try:
        # Get user with fresh data from DB
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(current_user.id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not user.location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has no location set. Please update user location first.",
            )

        # Extract user coordinates from Geography type
        # Cast Geography to Geometry to use ST_Y and ST_X functions
        coords_result = await db.execute(
            select(
                geo_func.ST_Y(cast(user.location, geoalchemy2.Geometry)).label("lat"),
                geo_func.ST_X(cast(user.location, geoalchemy2.Geometry)).label("lng"),
            )
        )
        coords = coords_result.first()

        if not coords:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract user location coordinates",
            )

        # Get recommendations
        service = GeospatialService(db)
        recommendations = await service.get_recommendations_for_user(
            user_id=current_user.id,
            radius_km=radius,
            skip=skip,
            limit=limit,
        )

        # Format response
        recommendation_items = [
            EventRecommendation(
                event=rec["event"],
                distance_km=rec["distance_km"],
            )
            for rec in recommendations
        ]

        from app.config import settings
        radius_km = radius if radius is not None else settings.DEFAULT_SEARCH_RADIUS_KM

        return RecommendationsResponse(
            recommendations=recommendation_items,
            total=len(recommendation_items),
            user_latitude=float(coords.lat),
            user_longitude=float(coords.lng),
            radius_km=radius_km,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(e)}",
        )
