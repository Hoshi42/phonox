#!/usr/bin/env python3
"""
Update Spotify URLs for Jan's records.
This is a helper script to fix the Spotify URLs after the backend fix.
"""

import requests
import json

API_BASE = "http://localhost:8000"

# Spotify URLs for Jan's albums
UPDATES = [
    {
        "record_id": "44e74e9d-a544-4438-8bb3-8a818b628657",  # Danzig - Danzig
        "spotify_url": "https://open.spotify.com/album/4XnGPn3Ht1LgLCpA7yXGa6"
    },
    {
        "record_id": "411a0f8d-cab5-4bf9-bbc0-7c7b8559fc0b",  # Igor - Igor
        "spotify_url": "https://open.spotify.com/album/5qGDYN8kEpPlLfmNM3kXoX"
    }
]

def update_spotify_urls():
    """Send batch update request to backend."""
    url = f"{API_BASE}/api/register/batch-update-spotify"
    
    payload = {
        "updates": UPDATES
    }
    
    print(f"📡 Sending batch update to {url}")
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.put(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        print(f"\n✅ Success!")
        print(f"Updated: {result['updated']}/{result['total']}")
        
        for update_result in result['results']:
            if update_result.get('success'):
                print(f"  ✅ {update_result['artist']} - {update_result['title']}")
                print(f"     {update_result['spotify_url']}")
            else:
                print(f"  ❌ {update_result['record_id']}: {update_result.get('error')}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    update_spotify_urls()
