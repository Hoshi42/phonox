"""
Database migration for image storage optimization.

This migration adds support for in-memory image storage (Base64) 
to avoid disk clutter while maintaining backward compatibility.

Changes:
- Make file_path OPTIONAL (nullable=True)
- Add image_data_base64 column for Base64-encoded images
- Add migration script for existing images
"""

import os
import base64
from datetime import datetime
from sqlalchemy import text

# Run this migration with: python migrate_images.py

def migrate_images_to_base64(db_session, upload_dir="/app/uploads"):
    """
    Optional: Migrate existing disk-based images to Base64 format.
    
    This reduces disk usage and centralizes image storage in the database.
    Can be run anytime and is safe (keeps file_path as backup).
    
    Usage:
        from backend.database import SessionLocal
        from migrate_images import migrate_images_to_base64
        
        db = SessionLocal()
        migrate_images_to_base64(db)
        db.close()
    """
    from backend.database import VinylImage
    
    migrated = 0
    failed = 0
    
    # Find all images with file_path but no image_data_base64
    images = db_session.query(VinylImage).filter(
        VinylImage.file_path.isnot(None),
        VinylImage.image_data_base64.is_(None)
    ).all()
    
    print(f"Found {len(images)} images to migrate")
    
    for image in images:
        try:
            # Read from disk
            if os.path.exists(image.file_path):
                with open(image.file_path, 'rb') as f:
                    image_data = f.read()
                    # Encode to Base64
                    image.image_data_base64 = base64.b64encode(image_data).decode('utf-8')
                    migrated += 1
                    
                    if migrated % 10 == 0:
                        print(f"  Migrated {migrated}/{len(images)} images...")
            else:
                print(f"  ⚠️ File not found: {image.file_path}")
                failed += 1
                
        except Exception as e:
            print(f"  ❌ Error migrating {image.filename}: {e}")
            failed += 1
    
    # Commit changes
    db_session.commit()
    
    print(f"\n✅ Migration complete:")
    print(f"  - Migrated: {migrated} images")
    print(f"  - Failed: {failed} images")
    print(f"  - Total: {len(images)} images")
    
    # You can now optionally delete the disk files
    # After verifying the migration was successful
    print(f"\n💡 Next step: Verify database backup before deleting disk files")
    print(f"   rm -rf {upload_dir}/*")


# SQL migration script for direct database updates
MIGRATION_SQL = """
-- Make file_path optional (if not already)
ALTER TABLE vinyl_images 
  ALTER COLUMN file_path DROP NOT NULL;

-- Add image_data_base64 column if it doesn't exist
ALTER TABLE vinyl_images 
  ADD COLUMN IF NOT EXISTS image_data_base64 TEXT;

-- Create index for efficient querying
CREATE INDEX IF NOT EXISTS idx_vinyl_images_storage_type 
  ON vinyl_images(CASE WHEN image_data_base64 IS NOT NULL THEN 'memory' ELSE 'disk' END);
"""

if __name__ == "__main__":
    from backend.database import SessionLocal
    
    print("🚀 Starting image storage migration...\n")
    
    db = SessionLocal()
    
    try:
        # Run the migration
        migrate_images_to_base64(db)
        print("\n✅ Migration successful!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
    finally:
        db.close()
