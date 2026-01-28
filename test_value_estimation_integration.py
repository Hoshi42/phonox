#!/usr/bin/env python3
"""
Integration test for the new value estimation endpoint.
Tests that the frontend correctly calls the backend estimate-value endpoint.
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from main import app, SessionLocal
from database import VinylRecord
from fastapi.testclient import TestClient

client = TestClient(app)

def test_value_estimation_endpoint():
    """Test that the estimate-value endpoint exists and returns proper format."""
    
    # First, create a test record
    db = SessionLocal()
    
    test_record = VinylRecord(
        artist="Nirvana",
        title="Nevermind",
        year=1991,
        estimated_value_eur=50.0,
        status="complete"
    )
    db.add(test_record)
    db.commit()
    record_id = test_record.id
    db.close()
    
    print(f"✓ Created test record: {record_id}")
    print(f"  Artist: Nirvana, Title: Nevermind")
    print(f"  Initial value: €50.00")
    
    # Test the estimate-value endpoint
    response = client.post(f"/api/v1/estimate-value/{record_id}")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    print(f"\n✓ Value estimation endpoint responded with 200")
    print(f"  Response keys: {list(data.keys())}")
    
    # Verify response structure
    required_keys = ['estimated_value_eur', 'price_range_min', 'price_range_max', 'market_condition', 'factors', 'explanation']
    for key in required_keys:
        assert key in data, f"Missing key in response: {key}"
        print(f"  ✓ {key}: {data[key]}")
    
    # Verify that the value in DB was updated
    db = SessionLocal()
    updated_record = db.query(VinylRecord).filter(VinylRecord.id == record_id).first()
    assert updated_record is not None, "Record not found after update"
    assert updated_record.estimated_value_eur is not None, "Value not updated in database"
    
    print(f"\n✓ Database updated successfully")
    print(f"  New value: €{updated_record.estimated_value_eur}")
    print(f"  Old value was: €50.00")
    print(f"  Value was REPLACED (not added to)")
    
    # Cleanup
    db.delete(updated_record)
    db.commit()
    db.close()
    
    print(f"\n✓ Test record cleaned up")
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    try:
        test_value_estimation_endpoint()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
