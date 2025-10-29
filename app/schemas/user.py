"""Pydantic schemas for User endpoints."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr = Field(..., description="User email address")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="User location latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="User location longitude")

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    """Schema for user response."""

    id: UUID
    name: str
    email: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    model_config = {"from_attributes": True}


class LocationUpdate(BaseModel):
    """Schema for updating user location."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")

    model_config = {"from_attributes": True}
