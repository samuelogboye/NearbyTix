"""Tests for authentication API endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.auth import verify_password, decode_access_token


@pytest.mark.asyncio
class TestRegisterEndpoint:
    """Tests for POST /api/v1/auth/register."""

    async def test_register_success(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test successful user registration."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "name": "New User",
                "email": "newuser@example.com",
                "password": "securepassword123",
                "latitude": 37.7749,
                "longitude": -122.4194,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "New User"
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "created_at" in data
        assert "hashed_password" not in data  # Password should not be in response

        # Verify user was created in database
        from sqlalchemy import select

        result = await db_session.execute(select(User).where(User.email == "newuser@example.com"))
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.name == "New User"
        assert verify_password("securepassword123", user.hashed_password)

    async def test_register_without_location(self, async_client: AsyncClient):
        """Test registration without location (optional field)."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "name": "No Location User",
                "email": "noloc@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "noloc@example.com"

    async def test_register_duplicate_email(self, async_client: AsyncClient, test_user: User):
        """Test registration with existing email."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "name": "Duplicate",
                "email": test_user.email,  # Already exists
                "password": "password123",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    async def test_register_invalid_email(self, async_client: AsyncClient):
        """Test registration with invalid email format."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "name": "Invalid Email",
                "email": "not-an-email",
                "password": "password123",
            },
        )

        assert response.status_code == 422  # Validation error

    async def test_register_short_password(self, async_client: AsyncClient):
        """Test registration with password too short."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "name": "Short Password",
                "email": "short@example.com",
                "password": "123",  # Too short
            },
        )

        assert response.status_code == 422

    async def test_register_missing_required_fields(self, async_client: AsyncClient):
        """Test registration with missing required fields."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "incomplete@example.com",
                # Missing name and password
            },
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login."""

    async def test_login_success(self, async_client: AsyncClient, test_user: User):
        """Test successful login."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",  # From test_user fixture
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Verify token contains correct user info
        payload = decode_access_token(data["access_token"])
        assert payload is not None
        assert payload["sub"] == str(test_user.id)
        assert payload["email"] == test_user.email

    async def test_login_wrong_password(self, async_client: AsyncClient, test_user: User):
        """Test login with incorrect password."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with email that doesn't exist."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "doesnotexist@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    async def test_login_invalid_email_format(self, async_client: AsyncClient):
        """Test login with invalid email format."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "not-an-email",
                "password": "password123",
            },
        )

        assert response.status_code == 422  # Validation error

    async def test_login_missing_fields(self, async_client: AsyncClient):
        """Test login with missing fields."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                # Missing password
            },
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestAuthenticationRequired:
    """Tests for endpoints that require authentication."""

    async def test_access_protected_endpoint_without_auth(self, async_client: AsyncClient):
        """Test accessing protected endpoint without authentication token."""
        response = await async_client.get("/api/v1/users/me")

        assert response.status_code == 403  # Forbidden

    async def test_access_protected_endpoint_with_invalid_token(self, async_client: AsyncClient):
        """Test accessing protected endpoint with invalid token."""
        response = await async_client.get(
            "/api/v1/users/me", headers={"Authorization": "Bearer invalid_token_here"}
        )

        assert response.status_code == 401  # Unauthorized

    async def test_access_protected_endpoint_with_valid_token(
        self, async_client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """Test accessing protected endpoint with valid token."""
        response = await async_client.get("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email

    async def test_token_expiration_format(self, test_user: User):
        """Test that JWT token has expiration claim."""
        from app.utils.auth import create_access_token

        token = create_access_token(data={"sub": str(test_user.id), "email": test_user.email})
        payload = decode_access_token(token)

        assert payload is not None
        assert "exp" in payload  # Expiration time
        assert "sub" in payload  # Subject (user ID)

    async def test_access_with_expired_token(self, async_client: AsyncClient):
        """Test accessing endpoint with expired token."""
        from datetime import timedelta
        from app.utils.auth import create_access_token

        # Create token that expires immediately
        expired_token = create_access_token(
            data={"sub": "user-id", "email": "test@example.com"}, expires_delta=timedelta(seconds=-1)
        )

        response = await async_client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401
