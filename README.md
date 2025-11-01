
# NearbyTix - Event Ticketing System

  

A production-ready FastAPI-based event ticketing system with geospatial matching capabilities.

  

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)](https://fastapi.tiangolo.com)

[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)

[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-orange.svg)](https://postgis.net/)

[![Celery](https://img.shields.io/badge/Celery-5.3.6-green.svg)](https://docs.celeryproject.org)

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

  

## Features

  

- ✅ **JWT Authentication**: Secure registration and login with bcrypt password hashing

- ✅ **Event Management**: Create and manage events with geospatial venue data

- ✅ **Atomic Ticket Reservation**: Prevents overselling with database locking

- ✅ **Automatic Expiration**: Tickets expire in 2 minutes if unpaid

- ✅ **Background Workers**: Celery for async task processing

- ✅ **Geospatial Recommendations**: Find nearby events using PostGIS

- ✅ **User Management**: Secure user profiles with location-based features

- ✅ **Complete Docker Setup**: One command to run everything

  

## Quick Start

  

```bash

# Start all services

docker compose  up  --build

  

# Access API documentation

http://localhost:8000/docs

```

  

That's it! The application is now running with:

- FastAPI API server (port 8000)

- PostgreSQL with PostGIS (port 5432)

- Redis (port 6379)

- Celery worker and beat scheduler

  

## API Endpoints

  

### Authentication 🔐

-  `POST /api/v1/auth/register` - Register new user

-  `POST /api/v1/auth/login` - Login and get JWT token

  

### Events (Public)

-  `POST /api/v1/events/` - Create event

-  `GET /api/v1/events/` - List events

-  `GET /api/v1/events/{id}` - Get event details

  

### Tickets (Protected - Requires Auth 🔒)

-  `POST /api/v1/tickets/` - Reserve ticket for authenticated user

-  `POST /api/v1/tickets/{id}/pay` - Pay for ticket (own tickets only)

-  `GET /api/v1/tickets/{id}` - Get ticket details (own tickets only)

-  `GET /api/v1/tickets/my-tickets` - Get my ticket history

  

### Users (Protected - Requires Auth 🔒)

-  `GET /api/v1/users/me` - Get my profile

-  `PUT /api/v1/users/me/location` - Update my location

  

### Recommendations (Protected - Requires Auth 🔒)

-  `GET /api/v1/for-you/?radius={km}` - Get personalized nearby events

  

## Architecture

  

Built with clean architecture principles:

  

```

API Layer → Service Layer → Repository Layer → Models Layer

```

  

-  **Repository Pattern**: Database operations abstraction

-  **Service Layer**: Business logic and domain rules

-  **Atomic Operations**: SELECT FOR UPDATE prevents race conditions

-  **Background Tasks**: Celery for ticket expiration

  

## Technology Stack

  

-  **API**: FastAPI 0.109.0 (async)

-  **Database**: PostgreSQL 16 + PostGIS 3.4

-  **ORM**: SQLAlchemy 2.0 (async)

-  **Migrations**: Alembic 1.13.1

-  **Task Queue**: Celery 5.3.6 + Redis 7

-  **Validation**: Pydantic 2.5

-  **Containerization**: Docker + Docker Compose

  

## Critical Feature: Preventing Overselling

  

The ticket reservation system uses **SELECT FOR UPDATE** locking to prevent race conditions:

  

```python

# Lock event row during reservation

event = await db.execute(

select(Event).where(Event.id == event_id).with_for_update()

).scalar_one()

  

# Check availability while holding lock

if event.tickets_sold >= event.total_tickets:

raise EventSoldOutException()

  

# Create ticket and increment atomically

ticket = await create_ticket(...)

event.tickets_sold += 1

await db.commit() # Release lock

```

  

This ensures multiple concurrent requests cannot oversell tickets.

  

## Testing

  

```bash

# Install dev dependencies

docker compose  exec  api  pip  install  -r  requirements-dev.txt

  

# Run all tests

docker compose  exec  api  pytest  tests/  -v

  

# Run with coverage

docker compose  exec  api  pytest  tests/  --cov=app  --cov-report=html

```

  

## Database Migrations

  

```bash

# Create migration

docker compose  exec  api  alembic  revision  --autogenerate  -m  "description"

  

# Apply migrations

docker compose  exec  api  alembic  upgrade  head

  

# Rollback

docker compose  exec  api  alembic  downgrade  -1

```

  

## Common Commands

  

Using Make:

```bash

make  help  # Show all commands

make  up  # Start services

make  logs  # View logs

make  test  # Run tests

make  down  # Stop services

```

  

Using Docker Compose:

```bash

docker compose  up  --build  # Start and build

docker compose  logs  -f  api  # View logs

docker compose  down  -v  # Stop and remove data

```

  

## Project Structure

  

```

app/

├── api/ # API endpoints

├── services/ # Business logic

├── repositories/ # Database operations

├── models/ # SQLAlchemy models

├── schemas/ # Pydantic schemas

├── tasks/ # Celery tasks

└── celery_app.py # Celery configuration

  

alembic/ # Database migrations

tests/ # Test suite

docker-compose.yml # Service orchestration

```

  

## Environment Variables

  

See `.env.example` for configuration options. Key settings:

-  `DATABASE_URL` - PostgreSQL connection string

-  `REDIS_URL` - Redis connection string

-  `JWT_SECRET_KEY` - JWT secret key (change in production!)

-  `TICKET_EXPIRATION_TIME` - Ticket expiration (seconds)

-  `DEFAULT_SEARCH_RADIUS_KM` - Geospatial search radius

 


## Key Highlights

  

🔒 **Concurrency Safe**: Database locking prevents overselling

⏰ **Auto-Expiration**: Celery tasks handle ticket expiration

📍 **Location-Based**: PostGIS geospatial recommendations

🏗️ **Clean Architecture**: Repository and Service layer patterns

🐳 **Docker Ready**: Single command deployment

📚 **Well Documented**: Comprehensive guides and inline docs

✅ **Production Ready**: Error handling, validation, logging



---

  

Built with ❤️ using FastAPI, PostgreSQL, PostGIS, and Celery.
Samuel Ogboye
ogboyesam@gmail.com