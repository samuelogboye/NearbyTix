"""Pydantic schemas for recommendations."""
from typing import List
from pydantic import BaseModel

from app.schemas.event import EventListItem


class EventRecommendation(BaseModel):
    """Schema for a single event recommendation with distance."""

    event: EventListItem
    distance_km: float

    model_config = {"from_attributes": True}


class RecommendationsResponse(BaseModel):
    """Schema for recommendations response."""

    recommendations: List[EventRecommendation]
    total: int
    user_latitude: float
    user_longitude: float
    radius_km: float

    model_config = {"from_attributes": True}
