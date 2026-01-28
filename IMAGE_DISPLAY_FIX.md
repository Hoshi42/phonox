# Re-analysis Image Display Fix

## Problem
After re-analyzing a vinyl record with newly uploaded images, only the latest/newly uploaded image was shown in the panel, not all images.

## Root Cause
The re-analysis endpoint was:
1. Analyzing the newly uploaded images
2. Updating the record metadata
3. **BUT NOT saving the newly uploaded images to the database**

So the image display (which shows `record.metadata?.image_urls`) only showed the old/existing images from the database, not the newly analyzed ones.

Additionally, the `to_dict()` method in the VinylRecord model was not including `image_urls` in the metadata response, so even existing images weren't being properly returned.

## Solution Implemented

### 1. Backend: Save Images During Re-analysis
Updated `reanalyze_vinyl` endpoint in `/backend/api/routes.py` (lines 1128-1161) to:
- Save each newly uploaded file to disk (using `/app/uploads`)
- Create a `VinylImage` database record for each file
- This makes the images persistent and part of the record

```python
# Save newly uploaded images to the database
if len(files) > 0:
    logger.info(f"Saving {len(files)} newly uploaded images to database for record {record_id}")
    from backend.api.register import UPLOAD_DIR
    for file in files:
        # Read file, save to disk, create VinylImage record
        ...
```

### 2. Backend: Include Images in Response
Updated `to_dict()` method in `/backend/database.py` to:
- Fetch all related `VinylImage` records using the `images` relationship
- Generate image URLs like `/api/register/images/{image_id}`
- Include `image_urls` in the metadata dict that gets returned to frontend

```python
def to_dict(self) -> Dict[str, Any]:
    """Convert to dictionary."""
    # Get image URLs from relationships
    image_urls = [f"/api/register/images/{img.id}" for img in self.images]
    
    return {
        ...
        "metadata": {
            ...
            "image_urls": image_urls,  # NOW INCLUDED
        },
        ...
    }
```

### 3. Frontend: Clear Uploaded Images Cache
Updated `handleReanalyze` in `/frontend/src/App.tsx` (lines 328-336) to:
- After re-analysis completes successfully, set `uploadedImages` to empty array
- This prevents showing stale preview images
- Frontend will now only show images from `record.metadata?.image_urls` (which now includes all images)

```javascript
if (statusResponse.status === 'analyzed' || statusResponse.status === 'complete') {
  const updatedRecord = statusResponse as unknown as VinylRecord
  setRecord(updatedRecord)
  // Clear uploaded images since they're now saved to database
  setUploadedImages([])
}
```

## Data Flow After Fix

```
User uploads images + clicks re-analyze
    ↓
Backend receives new files + record_id
    ↓
Analyze all images (existing + new)
    ↓
✨ SAVE NEW IMAGES TO DISK & DATABASE ✨
    ↓
Update record metadata
    ↓
Return response with to_dict() that includes image_urls
    ↓
Frontend receives updated record with ALL images in metadata.image_urls
    ↓
Frontend clears uploadedImages preview state
    ↓
Component renders showing all images from metadata.image_urls
```

## Files Modified

1. `/home/hoshhie/phonox/backend/api/routes.py`
   - Lines 1128-1161: Added image saving logic to reanalyze endpoint

2. `/home/hoshhie/phonox/backend/database.py`
   - Lines 93-121: Updated `to_dict()` to include `image_urls` from relationships

3. `/home/hoshhie/phonox/frontend/src/App.tsx`
   - Lines 328-336: Changed to clear `uploadedImages` after successful re-analysis

## Result
✅ All images (existing + newly analyzed) now persist to database during re-analysis
✅ All images are returned in the response metadata
✅ Frontend displays all images from the database (not stale previews)
✅ Image count is accurate and consistent across the UI

## Test Scenario
1. Load a record with 2 existing images
2. Upload 1 new image
3. Click "Re-analyze"
4. Backend analyzes all 3 images together ✅
5. New image is saved to database ✅
6. Frontend response includes all 3 images in metadata.image_urls ✅
7. UI displays all 3 images ✅
8. Uploaded images preview state is cleared ✅
