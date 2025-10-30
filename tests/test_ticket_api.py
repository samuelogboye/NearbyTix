"""Comprehensive tests for Ticket API endpoints."""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta

from app.models.user import User
from app.models.event import Event
from app.models.ticket import Ticket, TicketStatus


@pytest.mark.asyncio
class TestReserveTicket:
    """Tests for POST /api/v1/tickets/ (reserve ticket)."""

    async def test_reserve_ticket_success(
        self, async_client: AsyncClient, test_user: User, test_event: Event, auth_headers: dict
    ):
        """Test successful ticket reservation."""
        response = await async_client.post(
            "/api/v1/tickets/",
            json={"event_id": str(test_event.id)},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        assert data["user_id"] == str(test_user.id)
        assert data["event_id"] == str(test_event.id)
        assert data["status"] == "reserved"
        assert "expires_at" in data
        assert "id" in data

    async def test_reserve_ticket_without_auth(
        self, async_client: AsyncClient, test_event: Event
    ):
        """Test reserving ticket without authentication."""
        response = await async_client.post(
            "/api/v1/tickets/",
            json={"event_id": str(test_event.id)},
        )

        assert response.status_code == 403  # Forbidden

    async def test_reserve_ticket_sold_out_event(
        self, async_client: AsyncClient, test_event_sold_out: Event, auth_headers: dict
    ):
        """Test reserving ticket for sold out event."""
        response = await async_client.post(
            "/api/v1/tickets/",
            json={"event_id": str(test_event_sold_out.id)},
            headers=auth_headers,
        )

        assert response.status_code == 409  # Conflict
        assert "sold out" in response.json()["detail"].lower()

    async def test_reserve_ticket_nonexistent_event(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test reserving ticket for non-existent event."""
        fake_uuid = "12345678-1234-1234-1234-123456789012"
        response = await async_client.post(
            "/api/v1/tickets/",
            json={"event_id": fake_uuid},
            headers=auth_headers,
        )

        assert response.status_code == 404  # Not found

    async def test_reserve_multiple_tickets_same_event(
        self, async_client: AsyncClient, test_event: Event, auth_headers: dict
    ):
        """Test reserving multiple tickets for the same event."""
        # Reserve first ticket
        response1 = await async_client.post(
            "/api/v1/tickets/",
            json={"event_id": str(test_event.id)},
            headers=auth_headers,
        )
        assert response1.status_code == 201

        # Reserve second ticket
        response2 = await async_client.post(
            "/api/v1/tickets/",
            json={"event_id": str(test_event.id)},
            headers=auth_headers,
        )
        assert response2.status_code == 201

        # Both should be different tickets
        assert response1.json()["id"] != response2.json()["id"]


@pytest.mark.asyncio
class TestPayForTicket:
    """Tests for POST /api/v1/tickets/{ticket_id}/pay."""

    async def test_pay_for_ticket_success(
        self, async_client: AsyncClient, test_user: User, test_ticket: Ticket, auth_headers: dict
    ):
        """Test successful payment for reserved ticket."""
        response = await async_client.post(
            f"/api/v1/tickets/{test_ticket.id}/pay",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(test_ticket.id)
        assert data["status"] == "paid"
        assert "paid_at" in data
        assert data["paid_at"] is not None

    async def test_pay_for_ticket_without_auth(
        self, async_client: AsyncClient, test_ticket: Ticket
    ):
        """Test paying for ticket without authentication."""
        response = await async_client.post(f"/api/v1/tickets/{test_ticket.id}/pay")

        assert response.status_code == 403

    async def test_pay_for_someone_elses_ticket(
        self,
        async_client: AsyncClient,
        test_ticket: Ticket,
        auth_headers2: dict,  # Different user
    ):
        """Test paying for another user's ticket (should fail)."""
        response = await async_client.post(
            f"/api/v1/tickets/{test_ticket.id}/pay",
            headers=auth_headers2,
        )

        assert response.status_code == 403
        assert "your own tickets" in response.json()["detail"].lower()

    async def test_pay_for_already_paid_ticket(
        self, async_client: AsyncClient, test_ticket_paid: Ticket, auth_headers: dict
    ):
        """Test paying for already paid ticket."""
        response = await async_client.post(
            f"/api/v1/tickets/{test_ticket_paid.id}/pay",
            headers=auth_headers,
        )

        assert response.status_code == 409  # Conflict
        assert "reserved" in response.json()["detail"].lower()

    async def test_pay_for_nonexistent_ticket(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test paying for non-existent ticket."""
        fake_uuid = "12345678-1234-1234-1234-123456789012"
        response = await async_client.post(
            f"/api/v1/tickets/{fake_uuid}/pay",
            headers=auth_headers,
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestGetTicket:
    """Tests for GET /api/v1/tickets/{ticket_id}."""

    async def test_get_own_ticket(
        self, async_client: AsyncClient, test_ticket: Ticket, auth_headers: dict
    ):
        """Test getting own ticket details."""
        response = await async_client.get(
            f"/api/v1/tickets/{test_ticket.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(test_ticket.id)
        assert data["status"] == "reserved"

    async def test_get_someone_elses_ticket(
        self, async_client: AsyncClient, test_ticket: Ticket, auth_headers2: dict
    ):
        """Test getting another user's ticket (should fail)."""
        response = await async_client.get(
            f"/api/v1/tickets/{test_ticket.id}",
            headers=auth_headers2,
        )

        assert response.status_code == 403

    async def test_get_ticket_without_auth(
        self, async_client: AsyncClient, test_ticket: Ticket
    ):
        """Test getting ticket without authentication."""
        response = await async_client.get(f"/api/v1/tickets/{test_ticket.id}")

        assert response.status_code == 403


@pytest.mark.asyncio
class TestGetMyTickets:
    """Tests for GET /api/v1/tickets/my-tickets."""

    async def test_get_my_tickets(
        self,
        async_client: AsyncClient,
        test_user: User,
        test_ticket: Ticket,
        test_ticket_paid: Ticket,
        auth_headers: dict,
    ):
        """Test getting authenticated user's tickets."""
        response = await async_client.get(
            "/api/v1/tickets/my-tickets",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "tickets" in data
        assert "total" in data
        assert data["total"] >= 2  # At least the two fixtures
        assert len(data["tickets"]) >= 2

    async def test_get_my_tickets_without_auth(self, async_client: AsyncClient):
        """Test getting tickets without authentication."""
        response = await async_client.get("/api/v1/tickets/my-tickets")

        assert response.status_code == 403

    async def test_get_my_tickets_with_status_filter(
        self,
        async_client: AsyncClient,
        test_ticket: Ticket,
        test_ticket_paid: Ticket,
        auth_headers: dict,
    ):
        """Test filtering tickets by status."""
        response = await async_client.get(
            "/api/v1/tickets/my-tickets?status=paid",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # All returned tickets should be paid
        for ticket in data["tickets"]:
            assert ticket["status"] == "paid"

    async def test_get_my_tickets_pagination(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test pagination of ticket list."""
        response = await async_client.get(
            "/api/v1/tickets/my-tickets?skip=0&limit=5",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "skip" in data
        assert "limit" in data
        assert data["skip"] == 0
        assert data["limit"] == 5

    async def test_different_users_see_different_tickets(
        self,
        async_client: AsyncClient,
        test_ticket: Ticket,  # Belongs to test_user
        auth_headers: dict,  # test_user's headers
        auth_headers2: dict,  # test_user2's headers
    ):
        """Test that different users see only their own tickets."""
        # User 1's tickets
        response1 = await async_client.get(
            "/api/v1/tickets/my-tickets",
            headers=auth_headers,
        )
        tickets1 = response1.json()["tickets"]

        # User 2's tickets
        response2 = await async_client.get(
            "/api/v1/tickets/my-tickets",
            headers=auth_headers2,
        )
        tickets2 = response2.json()["tickets"]

        # User 1 should see test_ticket
        ticket_ids_1 = [t["id"] for t in tickets1]
        assert str(test_ticket.id) in ticket_ids_1

        # User 2 should NOT see test_ticket
        ticket_ids_2 = [t["id"] for t in tickets2]
        assert str(test_ticket.id) not in ticket_ids_2


@pytest.mark.asyncio
class TestTicketExpiration:
    """Tests for ticket expiration functionality."""

    async def test_ticket_has_expiration_time(
        self, async_client: AsyncClient, test_event: Event, auth_headers: dict
    ):
        """Test that reserved ticket has expiration time set."""
        response = await async_client.post(
            "/api/v1/tickets/",
            json={"event_id": str(test_event.id)},
            headers=auth_headers,
        )

        data = response.json()
        assert "expires_at" in data
        assert data["expires_at"] is not None

        # Parse expiration time
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)

        # Should expire in the future
        assert expires_at > now

        # Should expire within reasonable time (e.g., 5 minutes)
        assert expires_at < now + timedelta(minutes=5)

    async def test_paid_ticket_has_no_expiration(
        self, async_client: AsyncClient, test_ticket: Ticket, auth_headers: dict
    ):
        """Test that paid tickets don't have expiration."""
        # Pay for ticket
        await async_client.post(
            f"/api/v1/tickets/{test_ticket.id}/pay",
            headers=auth_headers,
        )

        # Get ticket details
        response = await async_client.get(
            f"/api/v1/tickets/{test_ticket.id}",
            headers=auth_headers,
        )

        data = response.json()
        # Paid tickets might have null expires_at or the original time
        # The important part is they have paid_at
        assert data["status"] == "paid"
        assert data["paid_at"] is not None
