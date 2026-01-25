"""FastAPI application entry point."""

import logging
import os
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from backend.database import Base, VinylRecord, get_db
from backend.api.models import HealthCheckResponse
from backend.api.register import router as register_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://phonox:phonox123@localhost:5432/phonox")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Update the global SessionLocal in database module
import backend.database as db_module
db_module.SessionLocal = SessionLocal


def override_get_db():
    """Override get_db dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app startup/shutdown."""
    # Startup
    logger.info("Starting Phonox API server")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    yield

    # Shutdown
    logger.info("Shutting down Phonox API server")


# Create FastAPI app
app = FastAPI(
    title="Phonox API",
    description="AI-powered Vinyl Collection Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",     # Local dev
        "http://localhost:3000",     # Alternative local
        "http://localhost:8080",     # Alternative local
        "http://127.0.0.1:5173",     # Loopback
        "http://172.18.0.3:5173",    # Docker container IP
        "http://frontend:5173",      # Docker service name
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
