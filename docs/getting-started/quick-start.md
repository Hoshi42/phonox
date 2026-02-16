# Quick Start Guide

Get Phonox up and running in 3 simple steps, then identify your first vinyl record.

## Installation (3 Steps)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/phonox.git
cd phonox
```

### Step 2: Setup Environment with API Key

```bash
# Copy the environment template
cp .env.example .env

# Add your Anthropic API key
./phonox-cli configure --anthropic YOUR_ANTHROPIC_KEY
```

**Get your API key:** [console.anthropic.com](https://console.anthropic.com)

### Step 3: Install and Start

```bash
# Make executable and run (installs + starts everything)
chmod +x start-cli.sh
./start-cli.sh
```

The `start-cli.sh` script automatically:
- ✅ Builds Docker images
- ✅ Starts all services (database, backend, frontend)
- ✅ Initializes the database

**Done!** Services will be available at:
- Frontend: http://localhost:5173
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Using Phonox

### Step 1: Prepare Images

Get 1-5 clear photos of your vinyl record. Best results with:
- Front cover (album artwork)
- Back cover (tracklist, barcode)
- Vinyl label (pressing details)
- Good lighting, straight angle
- At least 300x300 pixels, max 10MB each

### Step 2: Upload & Analyze

1. Open **http://localhost:5173** in your browser
2. Drag images onto the upload zone (or click to select)
3. Select condition: Poor / Fair / Good / Very Good / Near Mint / Mint
4. Click **"Analyze"** button

System automatically:
- Uploads all images
- Analyzes with AI vision (Claude Sonnet 4)
- Extracts barcodes if visible
- Searches Discogs and MusicBrainz
- Shows results in 5-10 seconds

### Step 3: Review Results

VinylCard displays identified metadata:

```
Artist: The Beatles
Title: Abbey Road
Year: 1969
Label: Apple Records
Catalog: PCS 7088
Barcode: 5099969945724
Genres: Rock, Pop
```

### Step 4: Optional Actions

**Edit Metadata**
- Click any field to edit
- Correct artist, title, year, etc.
- Add personal notes

**Check Market Value**
- Click "Check Current Value"
- Gets EUR and USD prices
- Searches current market data

**Chat About Record**
- Ask questions in chat panel
- AI has record context
- Get pressing information

### Step 5: Save to Collection

1. Select your username from dropdown (or type new name)
2. Click **"Add to Register"** button
3. Record saved to PostgreSQL database
4. View anytime in "My Collection"

## Managing Your Collection

Click **"My Collection"** button (top right):
- View all saved records with thumbnails
- Filter by user/collector
- Click "View" to load record details
- Click "Delete" to remove records
- Generate analysis reports

## Tips for Best Results

### Image Quality
- 📸 Clear, well-lit photos
- 🎯 Include barcode when visible
- 📐 Straight angle, avoid glare
- 📚 Multiple images improve accuracy (1-5 images)

### Barcode Detection
- UPC/EAN barcodes enable direct database lookup
- Photo of back cover usually has barcode
- Automatic extraction saves time
- Most accurate identification method

### Improve Identification
- Upload front + back + label for best results
- Use chat to refine uncertain identifications
- Edit fields manually if needed
- Re-analyze with better photos if accuracy low

### Collection Management
- Use meaningful usernames/tags
- Add notes about condition, pressing, source
- Check values periodically
- Keep backup of database

## Common Questions

**Q: How many images should I upload?**
A: 1-5 images. More images = better accuracy. Include front, back, and label when possible.

**Q: How long does identification take?**
A: Usually 5-10 seconds. First request may take slightly longer.

**Q: Can I edit the results?**
A: Yes! Click any field in VinylCard to edit. Changes are saved when you update or add to register.

**Q: How accurate is barcode detection?**
A: Very accurate when barcode is visible and clear. Directly looks up in databases.

**Q: Can I add more images later?**
A: Yes! Load record from collection, click "Add Image" button in VinylCard.

**Q: Where are images stored?**
A: Locally in `./uploads/` directory with references in PostgreSQL database.

## Next Steps

- 📖 Read [Full Upload Guide](../user-guide/uploading.md)
- 🗂️ Learn [Collection Management](../user-guide/collection.md)
- 💬 Explore [Chat Features](../user-guide/chat.md)
- 🔧 Review [API Reference](../api/endpoints.md)

## Troubleshooting

**Image upload fails?**
- Check file size (max 10MB per image)
- Try JPEG or PNG format
- Check internet connection

**No results after 30 seconds?**
- Check backend logs: `docker-compose logs backend`
- Verify API keys in `.env`
- Try refreshing page

**Still stuck?**
- Check [Database Connection Guide](../database-retry.md) for connection issues
- Search [GitHub Issues](https://github.com/your-username/phonox/issues)
