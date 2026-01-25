"""Register API endpoints for vinyl record collection management."""

import os
import uuid
import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db, VinylRecord, VinylImage

router = APIRouter(prefix="/register", tags=["register"])

# Upload directory
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class RegisterRecordRequest(BaseModel):
    record_id: str
    estimated_value_eur: Optional[float] = None
    condition: Optional[str] = None
    user_notes: Optional[str] = None
    spotify_url: Optional[str] = None


class RegisterRecordResponse(BaseModel):
    id: str
    artist: Optional[str] = None
    title: Optional[str] = None
    year: Optional[int] = None
    label: Optional[str] = None
    spotify_url: Optional[str] = None
    catalog_number: Optional[str] = None
    genres: Optional[List[str]] = None
    estimated_value_eur: Optional[float] = None
    condition: Optional[str] = None
    user_notes: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    image_urls: List[str] = []

    class Config:
        from_attributes = True


@router.get("/", response_model=List[RegisterRecordResponse])
async def get_register(db: Session = Depends(get_db)):
    """Get all records in the user's register."""
    records = db.query(VinylRecord).filter(VinylRecord.in_register == True).all()
    
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
        image_urls = [f"/register/images/{img.id}" for img in record.images]
        
        result.append(RegisterRecordResponse(
            id=record.id,
            artist=record.artist,
            title=record.title,
            year=record.year,
            label=record.label,
            spotify_url=record.spotify_url,
            catalog_number=record.catalog_number,
            genres=genres,
            estimated_value_eur=record.estimated_value_eur,
            condition=record.condition,
            user_notes=record.user_notes,
            confidence=record.confidence,
            created_at=record.created_at,
            updated_at=record.updated_at,
            image_urls=image_urls
        ))
    
    return result


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
    image_urls = [f"/register/images/{img.id}" for img in record.images]
    
    return RegisterRecordResponse(
        id=record.id,
        artist=record.artist,
        title=record.title,
        year=record.year,
        label=record.label,
        spotify_url=record.spotify_url,
        catalog_number=record.catalog_number,
        genres=genres,
        estimated_value_eur=record.estimated_value_eur,
        condition=record.condition,
        user_notes=record.user_notes,
        confidence=record.confidence,
        created_at=record.created_at,
        updated_at=record.updated_at,
        image_urls=image_urls
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
    
    # Update fields
    if request.estimated_value_eur is not None:
        record.estimated_value_eur = request.estimated_value_eur
    if request.condition is not None:
        record.condition = request.condition
    if request.user_notes is not None:
        record.user_notes = request.user_notes
    if request.spotify_url is not None:
        record.spotify_url = request.spotify_url
    
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
    image_urls = [f"/register/images/{img.id}" for img in record.images]
    
    return RegisterRecordResponse(
        id=record.id,
        artist=record.artist,
        title=record.title,
        year=record.year,
        label=record.label,
        spotify_url=record.spotify_url,
        catalog_number=record.catalog_number,
        genres=genres,
        estimated_value_eur=record.estimated_value_eur,
        condition=record.condition,
        user_notes=record.user_notes,
        confidence=record.confidence,
        created_at=record.created_at,
        updated_at=record.updated_at,
        image_urls=image_urls
    )


@router.delete("/{record_id}")
async def remove_from_register(record_id: str, db: Session = Depends(get_db)):
    """Remove a record from the register."""
    record = db.query(VinylRecord).filter(
        VinylRecord.id == record_id,
        VinylRecord.in_register == True
    ).first()
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
            "url": f"/register/images/{vinyl_image.id}"
        })
    
    db.commit()
    
    return {"uploaded_images": uploaded_images}