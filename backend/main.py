"""FastAPI application entry point."""

import logging
import os
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database import Base, VinylRecord, get_db
from backend.db_connection import DatabaseConnectionManager
from backend.api.models import HealthCheckResponse
from backend.api.register import router as register_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://phonox:phonox123@localhost:5432/phonox")

# Initialize database connection manager with retry logic
db_manager = DatabaseConnectionManager(
    database_url=DATABASE_URL,
    max_retries=int(os.getenv("DB_MAX_RETRIES", "5")),
    initial_retry_delay=int(os.getenv("DB_RETRY_DELAY", "2")),
    max_retry_delay=int(os.getenv("DB_MAX_RETRY_DELAY", "30")),
)

# This will be set after successful connection
engine = None
SessionLocal = None


def override_get_db():
    """Override get_db dependency to ensure SessionLocal is set."""
    if SessionLocal is None:
        raise HTTPException(
            status_code=503,
            detail="Database connection not available. Server is initializing.",
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app startup/shutdown."""
    global engine, SessionLocal
    
    # Startup
    logger.info("Starting Phonox API server")
    
    try:
        # Connect to database with retries
        db_manager.connect()
        engine = db_manager.get_engine()
        SessionLocal = db_manager.get_session_maker()
        
        # Update the global SessionLocal in database module
        import backend.database as db_module
        db_module.SessionLocal = SessionLocal
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
        
    except Exception as e:
        logger.critical(f"❌ Failed to initialize database: {e}")
        logger.critical("Application startup failed. Database connection is required.")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Phonox API server")
    if engine:
        db_manager.close()


# Create FastAPI app
app = FastAPI(
    title="Phonox API",
    description="AI-powered Vinyl Collection Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware FIRST - must be added before other middleware for proper functionality
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development including 192.x.x.x addresses
    allow_credentials=False,  # Must be False when using allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers to client
    max_age=3600,  # Cache preflight responses for 1 hour
)

# Override get_db dependency
app.dependency_overrides[get_db] = override_get_db

# Include routers
app.include_router(register_router)

# Import routes after app creation to avoid circular imports
from backend.api import routes  # noqa: E402, F401
# Include API routes
app.include_router(routes.router)


@app.get("/health", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(override_get_db)) -> HealthCheckResponse:
    """Health check endpoint."""
    dependencies = {
        "database": "connected",
        "claude_api": "available",
        "tavily_api": "available",
    }

    # Check database connectivity
    try:
        db.execute(text("SELECT 1"))
        dependencies["database"] = "connected"
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        dependencies["database"] = "disconnected"

    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        dependencies=dependencies,
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Phonox API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# Import routes after app creation to avoid circular imports
from backend.api import routes  # noqa: E402, F401
