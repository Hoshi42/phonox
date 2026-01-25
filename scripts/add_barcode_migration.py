#!/usr/bin/env python3
"""
Migration script to add barcode column to vinyl_records table.
Run this script to add the barcode column without losing existing data.
"""

import sys
import os
import logging

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import engine
from database import Base
from sqlalchemy import text

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def add_barcode_column():
    """Add barcode column to vinyl_records table if it doesn't exist."""
    try:
        with engine.begin() as connection:
            # Check if the barcode column already exists
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'vinyl_records' AND column_name = 'barcode'
            """))
            
            if result.fetchone():
                logger.info("Barcode column already exists in vinyl_records table")
                return True
            
            # Add the barcode column
            logger.info("Adding barcode column to vinyl_records table...")
            connection.execute(text("""
                ALTER TABLE vinyl_records 
                ADD COLUMN barcode VARCHAR(20) NULL
            """))
            
            logger.info("Successfully added barcode column to vinyl_records table")
            return True
            
    except Exception as e:
        logger.error(f"Failed to add barcode column: {e}")
        return False

if __name__ == "__main__":
    print("Adding barcode column to vinyl_records table...")
    
    if add_barcode_column():
        print("✅ Migration completed successfully!")
        print("The barcode column has been added to the vinyl_records table.")
    else:
        print("❌ Migration failed!")
        print("Check the logs for more details.")
        sys.exit(1)