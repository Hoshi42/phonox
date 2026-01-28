# API Usage Examples

Real-world code examples for common tasks.

## Python Examples

### Complete Identification Workflow

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# 1. Upload image
with open('vinyl.jpg', 'rb') as f:
    response = requests.post(
        f"{BASE_URL}/api/v1/identify",
        files={'images': f}
    )
    record_id = response.json()['record_id']
    print(f"Record ID: {record_id}")

# 2. Poll for results
max_attempts = 150  # 5 minutes with 2s interval
attempt = 0
while attempt < max_attempts:
    result = requests.get(f"{BASE_URL}/api/v1/identify/{record_id}")
    data = result.json()
    
    if data['status'] == 'complete':
        break
    
    print(f"Status: {data['status']} (attempt {attempt})")
    time.sleep(2)
    attempt += 1

# 3. Display results
metadata = data['metadata']
print(f"Artist: {metadata['artist']}")
print(f"Title: {metadata['title']}")
print(f"Year: {metadata['year']}")
print(f"Value: €{metadata['estimated_value_eur']}")

# 4. Add to collection
user_response = requests.post(
    f"{BASE_URL}/api/register/add",
    json={
        "user_tag": "mycollector",
        "vinyl_record": metadata
    }
)
print(f"Added to collection: {user_response.json()['id']}")
```

### Batch Processing

```python
import os
import glob

vinyl_images = glob.glob("vinyl_records/*.jpg")

for image_path in vinyl_images:
    print(f"Processing: {image_path}")
    
    with open(image_path, 'rb') as f:
        response = requests.post(
            f"{BASE_URL}/api/v1/identify",
            files={'images': f}
        )
    
    if response.status_code == 202:
        record_id = response.json()['record_id']
        # Process result...
```

### Collection Management

```python
import requests
import json

BASE_URL = "http://localhost:8000"
user_tag = "mycollector"

# Get all records
response = requests.get(
    f"{BASE_URL}/api/register",
    params={"user_tag": user_tag}
)
records = response.json()
print(f"Total records: {len(records)}")

# Calculate collection value
total_value = sum(r['estimated_value_eur'] for r in records)
print(f"Collection value: €{total_value:.2f}")

# Export to JSON
with open('collection.json', 'w') as f:
    json.dump(records, f, indent=2)

# Find specific record
beatles_records = [r for r in records if 'Beatles' in r['artist']]
print(f"Beatles records: {len(beatles_records)}")

# Update a record
if beatles_records:
    record_id = beatles_records[0]['id']
    requests.put(
        f"{BASE_URL}/api/register/{record_id}",
        json={
            "user_tag": user_tag,
            "condition": "Excellent",
            "estimated_value_eur": 60.00
        }
    )
```

## JavaScript/TypeScript Examples

### React Hook

```typescript
import { useState } from 'react';

export function useVinylIdentify() {
  const [loading, setLoading] = useState(false);
  const [record, setRecord] = useState(null);
  const [error, setError] = useState(null);

  const identify = async (imageFile: File) => {
    setLoading(true);
    
    try {
      // Upload
      const formData = new FormData();
      formData.append('images', imageFile);
      
      const uploadRes = await fetch('/api/v1/identify', {
        method: 'POST',
        body: formData
      });
      
      const { record_id } = await uploadRes.json();
      
      // Poll
      let status = 'pending';
      let result = null;
      
      while (status === 'pending') {
        const res = await fetch(`/api/v1/identify/${record_id}`);
        result = await res.json();
        status = result.status;
        
        if (status === 'pending') {
          await new Promise(r => setTimeout(r, 2000));
        }
      }
      
      setRecord(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return { identify, record, loading, error };
}
```

### Fetch Helper

```typescript
const API_BASE = '/api/v1';

export async function identifyVinyl(imageFile: File) {
  const formData = new FormData();
  formData.append('images', imageFile);
  
  const res = await fetch(`${API_BASE}/identify`, {
    method: 'POST',
    body: formData
  });
  
  return res.json();
}

export async function pollResults(recordId: string) {
  const res = await fetch(`${API_BASE}/identify/${recordId}`);
  return res.json();
}

export async function chatAboutRecord(recordId: string, message: string) {
  const res = await fetch(`${API_BASE}/identify/${recordId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  
  return res.json();
}
```

## Bash Examples

### Upload and Wait for Results

```bash
#!/bin/bash

VINYL_IMAGE="$1"
API="http://localhost:8000/api/v1"

# Upload
echo "Uploading: $VINYL_IMAGE"
RESPONSE=$(curl -s -X POST "$API/identify" \
  -F "images=@$VINYL_IMAGE")

RECORD_ID=$(echo $RESPONSE | jq -r '.record_id')
echo "Record ID: $RECORD_ID"

# Poll until complete
while true; do
  RESULT=$(curl -s "$API/identify/$RECORD_ID")
  STATUS=$(echo $RESULT | jq -r '.status')
  
  if [ "$STATUS" = "complete" ]; then
    echo "✓ Identification complete"
    echo $RESULT | jq '.metadata'
    break
  else
    echo "Status: $STATUS"
    sleep 2
  fi
done
```

### Batch Add to Collection

```bash
#!/bin/bash

API="http://localhost:8000/api/register"
USER="collector1"

# Read records from CSV (artist,title,year,label)
while IFS=',' read -r artist title year label; do
  curl -X POST "$API/add" \
    -H "Content-Type: application/json" \
    -d '{
      "user_tag": "'$USER'",
      "vinyl_record": {
        "artist": "'$artist'",
        "title": "'$title'",
        "year": '$year',
        "label": "'$label'"
      }
    }'
done < collection.csv
```

## Error Handling

### Python

```python
import requests

try:
    response = requests.post(
        'http://localhost:8000/api/v1/identify',
        files={'images': f},
        timeout=10
    )
    response.raise_for_status()
    
except requests.exceptions.Timeout:
    print("Request timed out")
except requests.exceptions.ConnectionError:
    print("Connection error - is server running?")
except requests.exceptions.HTTPError as e:
    print(f"HTTP error: {e.response.status_code}")
    print(e.response.json())
```

### JavaScript

```typescript
async function identifyWithRetry(file: File, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const res = await fetch('/api/v1/identify', {
        method: 'POST',
        body: new FormData([['images', file]])
      });
      
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      
      return await res.json();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(r => setTimeout(r, 1000 * (i + 1)));
    }
  }
}
```

## More Examples

See [API Endpoints](endpoints.md) for request/response details.

Check the [GitHub Repository](https://github.com/your-username/phonox/tree/master/examples) for more examples.
