"""Integration tests for event API endpoints."""
import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_post_events_success_201(async_client: AsyncClient, test_user: User, auth_headers: dict):
    """Test POST /events/ creates an event successfully."""
    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    payload = {
        "title": "Tech Conference 2025",
        "description": "Annual tech conference",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "total_tickets": 500,
        "venue": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "venue_name": "Convention Center",
            "address_line1": "123 Main St",
            "city": "New York",
            "state": "NY",
            "country": "USA",
            "postal_code": "10001",
        },
    }

    response = await async_client.post("/api/v1/events/", json=payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Tech Conference 2025"
    assert data["total_tickets"] == 500
    assert data["tickets_sold"] == 0
    assert data["tickets_available"] == 500
    assert "id" in data
    assert data["latitude"] == 40.7128
    assert data["longitude"] == -74.0060


@pytest.mark.asyncio
async def test_post_events_invalid_data_422(async_client: AsyncClient, auth_headers: dict):
    """Test POST /events/ with invalid data returns 422."""
    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time - timedelta(hours=1)  # End before start (invalid)

    payload = {
        "title": "Invalid Event",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),  # Invalid: end before start
        "total_tickets": 100,
        "venue": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "venue_name": "Venue",
            "address_line1": "123 St",
            "city": "NYC",
            "state": "NY",
            "country": "USA",
            "postal_code": "10001",
        },
    }

    response = await async_client.post("/api/v1/events/", json=payload, headers=auth_headers)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_events_past_date_rejected(async_client: AsyncClient, auth_headers: dict):
    """Test that past events are rejected."""
    start_time = datetime.now(timezone.utc) - timedelta(days=1)  # Past
    end_time = start_time + timedelta(hours=3)

    payload = {
        "title": "Past Event",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "total_tickets": 100,
        "venue": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "venue_name": "Venue",
            "address_line1": "123 St",
            "city": "NYC",
            "state": "NY",
            "country": "USA",
            "postal_code": "10001",
        },
    }

    response = await async_client.post("/api/v1/events/", json=payload, headers=auth_headers)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_events_returns_list_200(async_client: AsyncClient, auth_headers: dict):
    """Test GET /events/ returns list of events."""
    # Create test events
    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    for i in range(3):
        payload = {
            "title": f"Event {i}",
            "start_time": (start_time + timedelta(days=i)).isoformat(),
            "end_time": (end_time + timedelta(days=i)).isoformat(),
            "total_tickets": 100,
            "venue": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "venue_name": "Venue",
                "address_line1": "123 St",
                "city": "NYC",
                "state": "NY",
                "country": "USA",
                "postal_code": "10001",
            },
        }
        await async_client.post("/api/v1/events/", json=payload, headers=auth_headers)

    # Get all events
    response = await async_client.get("/api/v1/events/")

    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert "total" in data
    assert data["total"] == 3
    assert len(data["events"]) == 3


@pytest.mark.asyncio
async def test_get_events_pagination_works(async_client: AsyncClient, auth_headers: dict):
    """Test that pagination works for GET /events/."""
    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    # Create 5 events
    for i in range(5):
        payload = {
            "title": f"Event {i}",
            "start_time": (start_time + timedelta(days=i)).isoformat(),
            "end_time": (end_time + timedelta(days=i)).isoformat(),
            "total_tickets": 100,
            "venue": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "venue_name": "Venue",
                "address_line1": "123 St",
                "city": "NYC",
                "state": "NY",
                "country": "USA",
                "postal_code": "10001",
            },
        }
        await async_client.post("/api/v1/events/", json=payload, headers=auth_headers)

    # Get first page (limit 2)
    response = await async_client.get("/api/v1/events/?skip=0&limit=2")
    data = response.json()
    assert len(data["events"]) == 2
    assert data["total"] == 5
    assert data["skip"] == 0
    assert data["limit"] == 2

    # Get second page
    response = await async_client.get("/api/v1/events/?skip=2&limit=2")
    data = response.json()
    assert len(data["events"]) == 2

    # Get third page
    response = await async_client.get("/api/v1/events/?skip=4&limit=2")
    data = response.json()
    assert len(data["events"]) == 1


@pytest.mark.asyncio
async def test_get_events_empty_list(async_client: AsyncClient):
    """Test GET /events/ with no events returns empty list."""
    response = await async_client.get("/api/v1/events/")

    assert response.status_code == 200
    data = response.json()
    assert data["events"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_events_upcoming_only_filter(async_client: AsyncClient, auth_headers: dict):
    """Test GET /events/ with upcoming_only filter."""
    venue = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "venue_name": "Venue",
        "address_line1": "123 St",
        "city": "NYC",
        "state": "NY",
        "country": "USA",
        "postal_code": "10001",
    }

    # Create near future event (starts soon)
    near_future_start = datetime.now(timezone.utc) + timedelta(days=1)
    near_future_end = near_future_start + timedelta(hours=3)
    payload_near = {
        "title": "Near Future Event",
        "start_time": near_future_start.isoformat(),
        "end_time": near_future_end.isoformat(),
        "total_tickets": 100,
        "venue": venue,
    }
    response1 = await async_client.post("/api/v1/events/", json=payload_near, headers=auth_headers)
    assert response1.status_code == 201

    # Create far future event
    far_future_start = datetime.now(timezone.utc) + timedelta(days=30)
    far_future_end = far_future_start + timedelta(hours=3)
    payload_far = {
        "title": "Far Future Event",
        "start_time": far_future_start.isoformat(),
        "end_time": far_future_end.isoformat(),
        "total_tickets": 100,
        "venue": venue,
    }
    response2 = await async_client.post("/api/v1/events/", json=payload_far, headers=auth_headers)
    assert response2.status_code == 201

    # Get all events
    response = await async_client.get("/api/v1/events/")
    data = response.json()
    assert data["total"] == 2

    # Get upcoming only (should return both future events)
    response = await async_client.get("/api/v1/events/?upcoming_only=true")
    data = response.json()
    assert data["total"] == 2  # Both events are upcoming


@pytest.mark.asyncio
async def test_get_event_by_id_success(async_client: AsyncClient, auth_headers: dict):
    """Test GET /events/{event_id} returns event details."""
    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    payload = {
        "title": "Test Event",
        "description": "Test Description",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "total_tickets": 100,
        "venue": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "venue_name": "Test Venue",
            "address_line1": "123 Test St",
            "city": "NYC",
            "state": "NY",
            "country": "USA",
            "postal_code": "10001",
        },
    }

    # Create event
    create_response = await async_client.post("/api/v1/events/", json=payload, headers=auth_headers)
    event_id = create_response.json()["id"]

    # Get event by ID
    response = await async_client.get(f"/api/v1/events/{event_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == event_id
    assert data["title"] == "Test Event"
    assert data["description"] == "Test Description"
    assert data["venue_name"] == "Test Venue"


@pytest.mark.asyncio
async def test_get_event_by_id_not_found(async_client: AsyncClient):
    """Test GET /events/{event_id} with non-existent ID returns 404."""
    from uuid import uuid4

    fake_id = str(uuid4())
    response = await async_client.get(f"/api/v1/events/{fake_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_post_events_invalid_coordinates(async_client: AsyncClient, auth_headers: dict):
    """Test that invalid coordinates are rejected."""
    start_time = datetime.now(timezone.utc) + timedelta(days=7)
    end_time = start_time + timedelta(hours=3)

    payload = {
        "title": "Invalid Location",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "total_tickets": 100,
        "venue": {
            "latitude": 100.0,  # Invalid (out of range)
            "longitude": -74.0060,
            "venue_name": "Venue",
            "address_line1": "123 St",
            "city": "NYC",
            "state": "NY",
            "country": "USA",
            "postal_code": "10001",
        },
    }

    response = await async_client.post("/api/v1/events/", json=payload, headers=auth_headers)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient):
    """Test /health endpoint."""
    response = await async_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_name" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Test root / endpoint."""
    response = await async_client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data
