#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, 'backend')

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.database import VinylRecord

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/phonox")
engine = create_engine(DATABASE_URL)

with Session(engine) as db:
    chat_records = db.query(VinylRecord).filter(VinylRecord.artist.ilike('Chat:%')).all()
    print(f"Found {len(chat_records)} record(s):\n")
    for record in chat_records:
        print(f"ID: {record.id}")
        print(f"Artist: {record.artist}")
        print(f"Title: {record.title}")
        print(f"User Tag: {record.user_tag}")
        print()
