"""FastAPI application entry point."""

import logging
import os
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Request, Response
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
    
    # Cleanup old temporary analysis records (older than 24 hours)
    try:
        from datetime import timedelta
        db = SessionLocal()
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        old_temp_records = db.query(VinylRecord).filter(
            VinylRecord.status == "analyzed",
            VinylRecord.in_register == False,
            VinylRecord.created_at < cutoff_time
        ).all()
        
        deleted_count = 0
        for record in old_temp_records:
            # Delete associated images first
            for image in record.images:
                try:
                    image_path = image.file_path
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        logger.info(f"Deleted image file: {image_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete image file: {e}")
            db.delete(record)
            deleted_count += 1
        
        if deleted_count > 0:
            db.commit()
            logger.info(f"Cleaned up {deleted_count} old temporary analysis records")
        db.close()
    except Exception as e:
        logger.warning(f"Cleanup of temporary records failed: {e}")

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

# Add CORS middleware - enhanced for mobile compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development including 192.x.x.x addresses
    allow_credentials=False,  # Must be False when using allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=[
        "*",
        "Content-Type",
        "Authorization", 
        "X-Requested-With",
        "Accept",
        "Origin",
        "User-Agent",
        "Cache-Control",
        "X-Mobile-Cache-Bust"
    ],
    expose_headers=[
        "*",
        "Content-Type",
        "X-Total-Count",
        "Access-Control-Allow-Origin"
    ],
    max_age=86400,  # Cache preflight responses for 24 hours
)

# Override get_db dependency
app.dependency_overrides[get_db] = override_get_db

# Add CORS debugging middleware
@app.middleware("http")
async def cors_debug_middleware(request: Request, call_next):
    """Debug middleware to log CORS-related information."""
    origin = request.headers.get("origin", "No Origin")
    method = request.method
    url = str(request.url)
    
    logger.info(f"CORS Debug - Method: {method}, URL: {url}, Origin: {origin}")
    logger.info(f"CORS Debug - Headers: {dict(request.headers)}")
    
    # Call the next middleware/route
    response = await call_next(request)
    
    # Log response headers
    logger.info(f"CORS Debug - Response Status: {response.status_code}")
    logger.info(f"CORS Debug - Response Headers: {dict(response.headers)}")
    
    return response

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
