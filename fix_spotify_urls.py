"""
Fix Spotify URLs for existing records by searching for them via web search.
This script updates records that have empty spotify_url fields.
"""

import os
import asyncio
from backend.agent.websearch import search_spotify_album
from backend.database import get_db, VinylRecord, init_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Initialize database
db_url = os.getenv("DATABASE_URL", "postgresql://phonox:phonox@db:5432/phonox")
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

async def fix_spotify_urls():
    """Find and update Spotify URLs for records without them."""
    db = SessionLocal()
    
    try:
        # Get all records without spotify URLs that are in register
        records = db.query(VinylRecord).filter(
            VinylRecord.spotify_url.is_(None) | (VinylRecord.spotify_url == ''),
            VinylRecord.in_register == True
        ).all()
        
        print(f"Found {len(records)} records without Spotify URLs")
        
        for record in records:
            if not record.artist or not record.title:
                print(f"⚠️ Skipping {record.id} - missing artist or title")
                continue
            
            try:
                print(f"🔍 Searching for Spotify URL: {record.artist} - {record.title}")
                spotify_url = await search_spotify_album(record.artist, record.title)
                
                if spotify_url:
                    record.spotify_url = spotify_url
                    print(f"✅ Found: {spotify_url}")
                else:
                    print(f"⚠️ No Spotify URL found for {record.artist} - {record.title}")
                    
            except Exception as e:
                print(f"❌ Error searching for {record.artist} - {record.title}: {e}")
                continue
        
        # Commit all changes
        db.commit()
        print(f"✅ Updated {len(records)} records")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(fix_spotify_urls())
