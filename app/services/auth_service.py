"""Authentication service for user registration and login."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.schemas.auth import UserRegister, UserLogin, Token
from app.schemas.user import UserResponse
from app.repositories.user_repository import UserRepository
from app.utils.auth import hash_password, verify_password, create_access_token
from app.models.user import User


class AuthService:
    """Service for handling user authentication."""

    def __init__(self, db: AsyncSession):
        """
        Initialize authentication service.

        Args:
            db: Database session
        """
        self.db = db
        self.user_repo = UserRepository(db)

    async def register_user(self, user_data: UserRegister) -> UserResponse:
        """
        Register a new user.

        Args:
            user_data: User registration data

        Returns:
            Created user response

        Raises:
            HTTPException: If email already exists
        """
        # Check if user already exists
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash password
        hashed_password = hash_password(user_data.password)

        # Create user
        user = await self.user_repo.create(
            name=user_data.name,
            email=user_data.email,
            hashed_password=hashed_password,
            latitude=user_data.latitude,
            longitude=user_data.longitude,
        )

        await self.db.commit()
        await self.db.refresh(user)

        return await self.user_repo.to_response(user)

    async def login_user(self, login_data: UserLogin) -> Token:
        """
        Authenticate user and return JWT token.

        Args:
            login_data: User login credentials

        Returns:
            JWT access token

        Raises:
            HTTPException: If credentials are invalid
        """
        # Get user by email
        user = await self.user_repo.get_by_email(login_data.email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )

        return Token(access_token=access_token, token_type="bearer")

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User model or None
        """
        from uuid import UUID
        return await self.user_repo.get_by_id(UUID(user_id))
