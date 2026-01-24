"""FastAPI application entry point."""

import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.database import Base, VinylRecord, get_db
from backend.api.models import HealthCheckResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "sqlite:///./phonox.db"  # Local SQLite for development
# DATABASE_URL = "postgresql://phonox:phonox@postgres:5432/phonox"  # Production

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # type: ignore[assignment]

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
    version="0.3.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Override get_db dependency
app.dependency_overrides[get_db] = override_get_db


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
        db.execute("SELECT 1")
        dependencies["database"] = "connected"
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        dependencies["database"] = "disconnected"

    return HealthCheckResponse(
        status="healthy",
        version="0.3.0",
        timestamp=datetime.utcnow(),
        dependencies=dependencies,
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Phonox API",
        "version": "0.3.0",
        "docs": "/docs",
        "health": "/health",
    }


# Import routes after app creation to avoid circular imports
from backend.api import routes  # noqa: E402, F401
