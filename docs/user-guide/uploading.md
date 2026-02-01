# Uploading Records

Learn how to upload and identify vinyl records in Phonox.

## Prerequisites

- Phonox running locally (http://localhost:5173)
- API keys configured in `.env`
- Clear photos of vinyl records

## Upload Process

### Step 1: Navigate to Upload

1. Open Phonox in your browser
2. You'll see the main interface with:
   - Chat panel (left)
   - Upload area (center)
   - Collection panel (right)

### Step 2: Select Image

Click the **"Upload Image"** button and choose from:
- **Take Photo** - Use your device camera
- **Upload File** - Select from your computer
- **From URL** - Paste image URL

### Step 3: Image Guidelines

For best results, use photos that show:

**✅ Good Images:**
- Album cover (front or back)
- Clear vinyl label
- Barcode (if visible)
- Well-lit and in focus
- Straight angle
- Minimum 300x300 pixels

**❌ Poor Images:**
- Blurry or out of focus
- Dark or poorly lit
- At extreme angles
- Too small
- Reflections/glare

### Step 4: Review Metadata

Phonox will automatically:
1. Extract barcode (if visible)
2. Analyze cover art
3. Search Discogs and MusicBrainz
4. Retrieve metadata
5. Estimate market value

Results display:
```
Artist: The Beatles
Title: Abbey Road
Year: 1969
Label: Apple Records
Confidence: 92%
Estimated Value: €45.50
```

## Improving Results

### Upload Multiple Images

For better accuracy, upload:
- Front cover
- Back cover
- Spine (if visible)
- Vinyl label

### Use Chat for Refinement

Ask clarifying questions:
- "Is this the 1975 pressing?"
- "What's the condition?"
- "Are there any cover variations?"

### Edit Manually

If the AI identification isn't perfect:
1. Click **"Edit"** button
2. Modify artist, title, year
3. Add notes about pressing details
4. Save

## Saving to Collection

### Add to Collection

1. Review the identified metadata
2. Click **"Add to Collection"**
3. Enter your collector tag (optional)
4. Confirm

The record is now saved to your collection!

### Edit After Saving

1. Go to **"Collection"** panel
2. Find the record
3. Click record to view details
4. Click **"Edit"** to modify:
   - Condition (poor/fair/good/excellent/near mint)
   - Personal notes
   - Estimated value
   - Rating
   - Spotify link

## Tips & Tricks

### Improve Identification Accuracy

- **Multiple uploads**: More images = better accuracy
- **Clear barcodes**: Helps with exact matching
- **Chat context**: Provide pressing information
- **Manual corrections**: Fix any errors immediately

### Organize Your Collection

- **Add tags**: Use collector tags for grouping
- **Notes**: Record pressing info, where acquired, etc.
- **Condition tracking**: Keep accurate condition info
- **Value updates**: Monitor market prices

### Troubleshooting

**Image upload fails:**
- Check file size (max 10MB recommended)
- Try JPEG or PNG format
- Check internet connection

**Identification is wrong:**
- Try clearer photo
- Upload back cover too
- Use chat to refine
- Edit manually

**Can't find record:**
- May be rare or recently released
- Try uploading barcode image
- Search Discogs manually for pressing info
- Chat with AI for alternatives

## Batch Upload (Advanced)

For uploading multiple records:

1. Upload first record, confirm results
2. Save to collection
3. Repeat for next record

Or use the API for programmatic upload:

```bash
curl -X POST http://localhost:8000/api/register/upload \
  -F "file=@album.jpg"
```

See [API Reference](../api/endpoints.md) for details.
