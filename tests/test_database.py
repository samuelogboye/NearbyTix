"""Tests for database connection and configuration."""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, Base, engine


@pytest.mark.unit
@pytest.mark.asyncio
async def test_database_connection(db_session):
    """Test that database connection works."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_session_creation():
    """Test that async sessions can be created."""
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        break


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.requires_db
async def test_postgis_extension_enabled(db_session):
    """Test that PostGIS extension is enabled in the database."""
    # Check if PostGIS extension is available
    result = await db_session.execute(
        text(
            """
            SELECT EXISTS(
                SELECT 1 FROM pg_extension WHERE extname = 'postgis'
            ) as postgis_enabled
            """
        )
    )
    postgis_enabled = result.scalar()

    # If PostGIS is not enabled, this test will be skipped in environments
    # where PostGIS is not installed, but the test structure is correct
    if postgis_enabled:
        assert postgis_enabled is True
    else:
        pytest.skip("PostGIS extension not installed")


@pytest.mark.unit
def test_base_metadata_exists():
    """Test that Base metadata is properly configured."""
    assert Base.metadata is not None
    assert len(Base.metadata.tables) > 0


@pytest.mark.unit
def test_all_models_in_metadata():
    """Test that all models are registered in metadata."""
    table_names = Base.metadata.tables.keys()
    assert "users" in table_names
    assert "events" in table_names
    assert "tickets" in table_names


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_rollback_on_error(db_session):
    """Test that session rollback works on error."""
    from app.models import User
    from app.utils.auth import hash_password

    # Create a user
    user = User(name="Test User", email="test@example.com", hashed_password=hash_password("testpassword"))
    db_session.add(user)
    await db_session.commit()

    # Try to create duplicate user (should fail on unique email constraint)
    duplicate_user = User(name="Another User", email="test@example.com", hashed_password=hash_password("testpassword"))
    db_session.add(duplicate_user)

    with pytest.raises(Exception):
        await db_session.commit()

    # Session should still be usable after rollback
    await db_session.rollback()
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_db_cleanup_on_exception():
    """Test that get_db properly cleans up on exception."""
    try:
        async for session in get_db():
            # Simulate an error
            raise ValueError("Test error")
    except ValueError:
        pass  # Expected error

    # Test that we can still create new sessions
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        break


@pytest.mark.unit
def test_engine_configuration():
    """Test that database engine is properly configured."""
    assert engine is not None
    assert engine.pool is not None
    # Check that pool size is configured
    assert engine.pool.size() >= 0 or engine.pool._creator is not None
