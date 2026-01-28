"""Register API endpoints for vinyl record collection management."""

import os
import uuid
import json
from typing import List, Optional, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db, VinylRecord, VinylImage

router = APIRouter(prefix="/api/register", tags=["register"])

# Upload directory
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Explicit OPTIONS handlers for mobile CORS compatibility
@router.options("/")
async def options_register():
    """Handle OPTIONS requests for register endpoint."""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400",
        }
    )


@router.options("/users")
async def options_users():
    """Handle OPTIONS requests for users endpoint."""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400",
        }
    )


class RegisterRecordRequest(BaseModel):
    record_id: str
    artist: Optional[str] = None
    title: Optional[str] = None
    year: Optional[int] = None
    label: Optional[str] = None
    catalog_number: Optional[str] = None
    barcode: Optional[str] = None
    genres: Optional[List[str]] = None
    estimated_value_eur: Optional[float] = None
    condition: Optional[str] = None
    user_notes: Optional[str] = None
    spotify_url: Optional[str] = None
    user_tag: Optional[str] = None


class RegisterRecordResponse(BaseModel):
    id: str
    artist: Optional[str] = None
    title: Optional[str] = None
    year: Optional[int] = None
    label: Optional[str] = None
    spotify_url: Optional[str] = None
    catalog_number: Optional[str] = None
    barcode: Optional[str] = None  # UPC/EAN barcode
    genres: Optional[List[str]] = None
    estimated_value_eur: Optional[float] = None
    condition: Optional[str] = None
    user_notes: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    image_urls: List[str] = []
    user_tag: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[RegisterRecordResponse])
async def get_register(user_tag: Optional[str] = None, db: Session = Depends(get_db)):
    """Get all records in the user's register."""
    query = db.query(VinylRecord).filter(VinylRecord.in_register == True)
    if user_tag:
        query = query.filter(VinylRecord.user_tag == user_tag)
    records = query.all()
    
    result = []
    for record in records:
        # Parse genres JSON
        genres = []
        if record.genres:
            try:
                genres = json.loads(record.genres)
            except (json.JSONDecodeError, TypeError):
                genres = []
        
        # Get image URLs
        image_urls = [f"/api/register/images/{img.id}" for img in record.images]
        
        result.append(RegisterRecordResponse(
            id=record.id,
            artist=record.artist,
            title=record.title,
            year=record.year,
            label=record.label,
            spotify_url=record.spotify_url,
            catalog_number=record.catalog_number,
            barcode=record.barcode,
            genres=genres,
            estimated_value_eur=record.estimated_value_eur,
            condition=record.condition,
            user_notes=record.user_notes,
            confidence=record.confidence,
            created_at=record.created_at,
            updated_at=record.updated_at,
            image_urls=image_urls,
            user_tag=record.user_tag
        ))
    
    return result


@router.get("/users", response_model=List[str])
async def get_users(db: Session = Depends(get_db)):
    """Get all distinct users who have records."""
    result = db.query(VinylRecord.user_tag).filter(
        VinylRecord.user_tag.isnot(None),
        VinylRecord.user_tag != ""
    ).distinct().all()
    
    return [row[0] for row in result if row[0]]


@router.post("/add", response_model=RegisterRecordResponse)
async def add_to_register(
    request: RegisterRecordRequest,
    db: Session = Depends(get_db)
):
    """Add a record to the register."""
    # Get the record
    record = db.query(VinylRecord).filter(VinylRecord.id == request.record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Update register fields
    record.in_register = True
    record.estimated_value_eur = request.estimated_value_eur
    record.condition = request.condition
    record.user_notes = request.user_notes
    if request.spotify_url is not None:
        record.spotify_url = request.spotify_url
    if request.user_tag is not None:
        record.user_tag = request.user_tag
    record.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(record)
    
    # Parse genres
    genres = []
    if record.genres:
        try:
            genres = json.loads(record.genres)
        except (json.JSONDecodeError, TypeError):
            genres = []
    
    # Get image URLs
    image_urls = [f"/api/register/images/{img.id}" for img in record.images]
    
    return RegisterRecordResponse(
        id=record.id,
        artist=record.artist,
        title=record.title,
        year=record.year,
        label=record.label,
        spotify_url=record.spotify_url,
        catalog_number=record.catalog_number,
        barcode=record.barcode,
        genres=genres,
        estimated_value_eur=record.estimated_value_eur,
        condition=record.condition,
        user_notes=record.user_notes,
        confidence=record.confidence,
        created_at=record.created_at,
        updated_at=record.updated_at,
        image_urls=image_urls,
        user_tag=record.user_tag
    )


@router.put("/update", response_model=RegisterRecordResponse)
async def update_register_record(
    request: RegisterRecordRequest,
    db: Session = Depends(get_db)
):
    """Update a record in the register."""
    # Get the record
    record = db.query(VinylRecord).filter(
        VinylRecord.id == request.record_id,
        VinylRecord.in_register == True
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found in register")
    
    # Update fields from request - use model_dump to get only provided fields
    # This allows sending None/null to explicitly clear a field
    update_data = request.model_dump(exclude_unset=True, exclude={'record_id'})
    
    for field, value in update_data.items():
        if field == 'genres':
            # Special handling for genres (uses set_genres method)
            if value:
                record.set_genres(value)
            else:
                record.set_genres([])
        else:
            # Set the field on the record (including None to clear)
            setattr(record, field, value)
    
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    
    # Parse genres
    genres = []
    if record.genres:
        try:
            genres = json.loads(record.genres)
        except (json.JSONDecodeError, TypeError):
            genres = []
    
    # Get image URLs
    image_urls = [f"/api/register/images/{img.id}" for img in record.images]
    
    return RegisterRecordResponse(
        id=record.id,
        artist=record.artist,
        title=record.title,
        year=record.year,
        label=record.label,
        spotify_url=record.spotify_url,
        catalog_number=record.catalog_number,
        barcode=record.barcode,
        genres=genres,
        estimated_value_eur=record.estimated_value_eur,
        condition=record.condition,
        user_notes=record.user_notes,
        confidence=record.confidence,
        created_at=record.created_at,
        updated_at=record.updated_at,
        image_urls=image_urls,
        user_tag=record.user_tag
    )


@router.delete("/{record_id}")
async def remove_from_register(record_id: str, user_tag: Optional[str] = None, db: Session = Depends(get_db)):
    """Remove a record from the register."""
    query = db.query(VinylRecord).filter(
        VinylRecord.id == record_id,
        VinylRecord.in_register == True
    )
    if user_tag:
        query = query.filter(VinylRecord.user_tag == user_tag)
    
    record = query.first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found in register")
    
    record.in_register = False
    record.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Record removed from register"}


@router.get("/images/{image_id}")
async def get_image(image_id: str, db: Session = Depends(get_db)):
    """Get an image file."""
    image = db.query(VinylImage).filter(VinylImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    if not os.path.exists(image.file_path):
        raise HTTPException(status_code=404, detail="Image file not found")
    
    return FileResponse(
        image.file_path,
        media_type=image.content_type,
        filename=image.filename
    )


@router.post("/images/{record_id}")
async def upload_images(
    record_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload images for a record."""
    record = db.query(VinylRecord).filter(VinylRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    uploaded_images = []
    
    for file in files:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            continue
            
        # Generate unique filename
        file_extension = os.path.splitext(file.filename or '')[1] or '.jpg'
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Create database record
        vinyl_image = VinylImage(
            record_id=record_id,
            filename=file.filename or unique_filename,
            content_type=file.content_type,
            file_size=len(content),
            file_path=file_path,
            is_primary=len(record.images) == 0  # First image is primary
        )
        
        db.add(vinyl_image)
        uploaded_images.append({
            "id": vinyl_image.id,
            "filename": vinyl_image.filename,
            "url": f"/api/register/images/{vinyl_image.id}"
        })
    
    db.commit()
    
    return {"uploaded_images": uploaded_images}


class UpdateSpotifyUrlRequest(BaseModel):
    """Request model for updating Spotify URLs."""
    updates: List[Dict[str, Optional[str]]] = []
    # updates is list of {record_id: str, spotify_url: str}


@router.put("/batch-update-spotify")
async def batch_update_spotify_urls(
    request: UpdateSpotifyUrlRequest,
    db: Session = Depends(get_db)
):
    """Batch update Spotify URLs for multiple records."""
    results = []
    
    for update in request.updates:
        record_id = update.get("record_id")
        spotify_url = update.get("spotify_url")
        
        if not record_id or not spotify_url:
            results.append({
                "record_id": record_id,
                "success": False,
                "error": "Missing record_id or spotify_url"
            })
            continue
        
        record = db.query(VinylRecord).filter(VinylRecord.id == record_id).first()
        if not record:
            results.append({
                "record_id": record_id,
                "success": False,
                "error": "Record not found"
            })
            continue
        
        record.spotify_url = spotify_url
        results.append({
            "record_id": record_id,
            "success": True,
            "artist": record.artist,
            "title": record.title,
            "spotify_url": spotify_url
        })
    
    db.commit()
    
    return {
        "updated": sum(1 for r in results if r.get("success")),
        "total": len(results),
        "results": results
    }