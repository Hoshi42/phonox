#!/usr/bin/env python3
"""
Cleanup script to remove "Chat:" entries from user_notes field.
This safely removes chat messages that were automatically appended to user_notes
while preserving any actual user-written notes.
"""

import os
import sys
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database import VinylRecord, Base

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/phonox"
)

def cleanup_chat_notes():
    """Find and clean chat entries from user_notes."""
    engine = create_engine(DATABASE_URL)
    
    with Session(engine) as db:
        # Find all records with "Chat:" in user_notes
        records_with_chat = db.query(VinylRecord).filter(
            VinylRecord.user_notes.ilike('%Chat:%')
        ).all()
        
        if not records_with_chat:
            print("✅ No chat entries found in user_notes.")
            return
        
        print(f"\n📋 Found {len(records_with_chat)} record(s) with chat entries:\n")
        
        for i, record in enumerate(records_with_chat, 1):
            print(f"{i}. {record.artist or 'Unknown'} - {record.title or 'Unknown'}")
            print(f"   Current notes:\n   {record.user_notes[:200]}...")
            print()
        
        # Ask for confirmation
        response = input("Clean these entries? (yes/no): ").strip().lower()
        if response not in ('yes', 'y'):
            print("❌ Cancelled.")
            return
        
        # Clean each record
        cleaned_count = 0
        for record in records_with_chat:
            if not record.user_notes:
                continue
            
            # Remove all "Chat: ..." lines (including leading/trailing whitespace and newlines)
            original = record.user_notes
            cleaned = re.sub(r'[\n\s]*Chat:[^\n]*', '', original)
            # Remove extra whitespace
            cleaned = '\n'.join(line for line in cleaned.split('\n') if line.strip())
            
            # Update or null out
            if cleaned.strip():
                record.user_notes = cleaned.strip()
            else:
                record.user_notes = None
            
            cleaned_count += 1
            print(f"✓ Cleaned: {record.artist or 'Unknown'} - {record.title or 'Unknown'}")
        
        # Commit changes
        db.commit()
        print(f"\n✅ Successfully cleaned {cleaned_count} record(s).")

if __name__ == "__main__":
    try:
        cleanup_chat_notes()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
