"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import init_db, close_db, get_db
from app.api import events, tickets, users, recommendations, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    # Note: Database tables should be created via Alembic migrations
    # init_db() is only for development/testing
    # await init_db()
    yield
    # Shutdown
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Event ticketing system with geospatial matching",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint with database connectivity check.

    Args:
        db: Database session

    Returns:
        Health status including database connectivity
    """
    health_status = {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": {
            "connected": False,
            "status": "unknown"
        }
    }

    # Check database connectivity
    try:
        # Execute a simple query to verify database connection
        result = await db.execute(text("SELECT 1"))
        result.scalar()

        health_status["database"]["connected"] = True
        health_status["database"]["status"] = "healthy"

        return JSONResponse(
            status_code=200,
            content=health_status
        )
    except Exception as e:
        # Database connection failed
        health_status["status"] = "unhealthy"
        health_status["database"]["connected"] = False
        health_status["database"]["status"] = f"error: {str(e)}"

        return JSONResponse(
            status_code=503,
            content=health_status
        )


@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint.

    Returns:
        Welcome message
    """
    return JSONResponse(
        content={
            "message": f"Welcome to {settings.APP_NAME} API",
            "version": settings.APP_VERSION,
            "docs": "/docs",
        }
    )


# Include routers
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(events.router, prefix=settings.API_PREFIX)
app.include_router(tickets.router, prefix=settings.API_PREFIX)
app.include_router(users.router, prefix=settings.API_PREFIX)
app.include_router(recommendations.router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
