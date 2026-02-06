# Uploading Records

Learn how to upload and identify vinyl records in Phonox.

## Prerequisites

- Phonox running locally (http://localhost:5173)
- API keys configured in `.env`
- Clear photos of vinyl records (1-5 images)

## Upload Process

### Step 1: Navigate to Upload

1. Open Phonox in your browser at http://localhost:5173
2. You'll see the main interface with:
   - Chat panel (left side)
   - Upload area with drag-and-drop zone (center)
   - Record display area (right side)
   - "My Collection" button (top right)

### Step 2: Upload Images

Phonox supports **1 to 5 images** per upload. You can:

**Drag and Drop:**
- Drag image files directly onto the upload zone
- Support for PNG, JPG, GIF, WebP formats
- Maximum 10MB per image

**Click to Upload:**
- Click the upload zone
- Select 1-5 images from your computer
- Multiple images improve identification accuracy

**Select Condition:**
- Choose record condition: Poor, Fair, Good, Very Good, Near Mint, Mint
- Default is "Good"
- Can be updated later in the collection

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

### Step 4: Automatic Analysis

After upload, Phonox automatically:
1. **Uploads images** - Displays progress for each image
2. **AI Vision Analysis** - Analyzes cover art and labels with Claude Vision
3. **Barcode Detection** - Extracts UPC/EAN barcodes if visible
4. **Web Search** - Searches Discogs, MusicBrainz, and other sources
5. **Metadata Extraction** - Retrieves artist, title, year, label, catalog number
6. **Results Display** - Shows identified record in VinylCard

Results display in the VinylCard:
```
Artist: The Beatles
Title: Abbey Road
Year: 1969
Label: Apple Records
Catalog: PCS 7088
Barcode: 5099969945724
Genres: Rock, Pop
```

### Step 5: Review Results

The VinylCard shows:
- **Metadata** - All identified information
- **Images** - Your uploaded photos
- **Evidence Chain** - How identification was determined
- **Edit Button** - Modify any field
- **Value Estimation** - Get current market price
- **Add to Collection** - Save to your register

## Improving Results

### Upload Multiple Images

For best accuracy, upload multiple images (up to 5):
- **Front cover** - Main identification
- **Back cover** - Additional catalog info
- **Vinyl label** - Pressing details
- **Spine** - Catalog numbers
- **Barcode** - Direct database lookup

### Use Chat for Questions

Ask the AI assistant:
- "Tell me more about this pressing"
- "What's special about this edition?"
- "What are similar albums?"
- "Who played on this record?"

### Edit Metadata

Click on any field in VinylCard to edit:
1. **Artist** - Click to modify
2. **Title** - Click to edit
3. **Year** - Change release year
4. **Label** - Update label name
5. **Catalog Number** - Correct catalog info
6. **Genres** - Add or remove genres
7. **User Notes** - Add personal notes
8. **Condition** - Update condition rating

Changes are saved automatically.

### Estimate Market Value

Click **"Check Current Value"** to:
- Search current market listings
- Get price estimates in EUR and USD
- See value ranges by condition
- View recent sales data

### Add or Remove Images

Manage images in your record:
- **Add Images** - Upload additional photos (max 5 total)
- **Remove Images** - Click X on any image thumbnail
- Useful for adding better photos later

## Saving to Collection

### Add to Your Register

1. Review the metadata in VinylCard
2. Select your username from dropdown (or create new)
3. Click **"Add to Register"** button
4. Record is saved to your collection

### View Your Collection

Click **"My Collection"** button to:
- View all saved records
- Search and filter
- Load records back into VinylCard
- Delete records
- Generate reports

## Re-analyzing Records

If identification isn't accurate:
1. Click **"Re-analyze"** button
2. Upload better/different images
3. System re-processes with new images
4. Updates metadata automatically

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
