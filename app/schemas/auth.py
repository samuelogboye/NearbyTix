"""Pydantic schemas for authentication."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Schema for user registration."""

    name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, max_length=100, description="User password (min 8 characters)")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude of user location")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude of user location")

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User password")

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")

    model_config = {"from_attributes": True}


class TokenData(BaseModel):
    """Schema for decoded JWT token data."""

    user_id: str = Field(..., description="User ID from token")
    email: Optional[str] = Field(None, description="User email from token")

    model_config = {"from_attributes": True}
