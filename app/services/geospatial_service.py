"""Geospatial service for location-based queries."""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2 import functions as geo_func

from app.models.event import Event
from app.models.user import User
from app.schemas.event import EventListItem
from app.config import settings


class GeospatialService:
    """Service for geospatial queries and recommendations."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def find_nearby_events(
        self,
        latitude: float,
        longitude: float,
        radius_km: Optional[float] = None,
        skip: int = 0,
        limit: int = 100,
        upcoming_only: bool = True,
    ) -> List[tuple[Event, float]]:
        """
        Find events near a location using PostGIS.

        Args:
            latitude: User latitude
            longitude: User longitude
            radius_km: Search radius in kilometers (default: from settings)
            skip: Number of records to skip
            limit: Maximum number of records to return
            upcoming_only: Only return future events

        Returns:
            List of tuples (Event, distance_km)
        """
        if radius_km is None:
            radius_km = settings.DEFAULT_SEARCH_RADIUS_KM

        # Create point from user coordinates (WGS84 - SRID 4326)
        user_location = func.ST_SetSRID(
            func.ST_MakePoint(longitude, latitude),
            4326
        )

        # Calculate distance in meters, convert to km
        distance_expr = geo_func.ST_Distance(
            geo_func.ST_GeogFromWKB(Event.location.data),
            func.cast(user_location, geo_func.Geography)
        )

        # Build query
        query = select(
            Event,
            (distance_expr / 1000).label("distance_km")  # Convert meters to km
        ).where(
            # Filter by radius (distance in meters)
            distance_expr <= radius_km * 1000
        )

        # Filter upcoming events only
        if upcoming_only:
            query = query.where(Event.start_time > datetime.utcnow())

        # Filter out sold out events
        query = query.where(Event.tickets_sold < Event.total_tickets)

        # Order by distance (closest first)
        query = query.order_by(distance_expr)

        # Pagination
        query = query.offset(skip).limit(limit)

        # Execute query
        result = await self.db.execute(query)
        results = result.all()

        return [(row.Event, row.distance_km) for row in results]

    async def get_recommendations_for_user(
        self,
        user_id: UUID,
        radius_km: Optional[float] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[dict]:
        """
        Get personalized event recommendations for a user based on their location.

        Args:
            user_id: User UUID
            radius_km: Search radius in kilometers (optional)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of event recommendations with distance
        """
        # Get user
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user or not user.location:
            return []

        # Extract user coordinates
        coords_result = await self.db.execute(
            select(
                geo_func.ST_Y(geo_func.ST_GeomFromWKB(user.location.data)).label("lat"),
                geo_func.ST_X(geo_func.ST_GeomFromWKB(user.location.data)).label("lng"),
            )
        )
        coords = coords_result.first()

        if not coords:
            return []

        # Find nearby events
        nearby_events = await self.find_nearby_events(
            latitude=float(coords.lat),
            longitude=float(coords.lng),
            radius_km=radius_km,
            skip=skip,
            limit=limit,
            upcoming_only=True,
        )

        # Format response
        recommendations = []
        for event, distance_km in nearby_events:
            recommendations.append({
                "event": EventListItem(
                    id=event.id,
                    title=event.title,
                    description=event.description,
                    start_time=event.start_time,
                    end_time=event.end_time,
                    tickets_available=event.tickets_available,
                    is_sold_out=event.is_sold_out,
                    venue_name=event.venue_name,
                    city=event.city,
                    state=event.state,
                ),
                "distance_km": round(distance_km, 2),
            })

        return recommendations

    async def calculate_distance(
        self,
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float,
    ) -> float:
        """
        Calculate distance between two points using PostGIS.

        Args:
            lat1: First point latitude
            lng1: First point longitude
            lat2: Second point latitude
            lng2: Second point longitude

        Returns:
            Distance in kilometers
        """
        point1 = func.ST_SetSRID(func.ST_MakePoint(lng1, lat1), 4326)
        point2 = func.ST_SetSRID(func.ST_MakePoint(lng2, lat2), 4326)

        distance_query = select(
            geo_func.ST_Distance(
                func.cast(point1, geo_func.Geography),
                func.cast(point2, geo_func.Geography)
            ).label("distance_meters")
        )

        result = await self.db.execute(distance_query)
        distance_meters = result.scalar()

        return distance_meters / 1000 if distance_meters else 0.0
