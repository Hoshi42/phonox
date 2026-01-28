# Quick Start Guide

Get your first vinyl record identified in 5 minutes.

## Step 1: Prepare an Image

Get a clear photo of a vinyl record cover. Best results with:
- Record sleeve/cover (clearly visible)
- Good lighting
- Straight angle (not too tilted)
- At least 300x300 pixels

## Step 2: Upload & Identify

1. Open **http://localhost:5173** in your browser
2. Click **"Upload Image"** button
3. Select your vinyl photo
4. Click **"Identify"**

The app will:
- Upload the image
- Analyze with AI vision
- Search for metadata
- Show results in ~5-10 seconds

## Step 3: Review Results

You'll see:

```
Artist: The Beatles
Title: Abbey Road
Year: 1969
Label: Apple Records
Confidence: 92%
Estimated Value: €45.50
```

**Actions:**
- ✅ **Confirm** - Save as-is
- ✏️ **Edit** - Modify details
- 🔄 **Re-analyze** - Upload more images
- 💬 **Chat** - Ask questions about the record

## Step 4: Add to Collection

1. Click **"Add to Collection"** button
2. Enter your name (saves as "collector1" by default)
3. Confirm

Your record is now saved! View it anytime in the **"My Records"** panel on the right.

## Step 5: Manage Collection

In **"My Records"** panel:
- **View Details** - Full record information
- **Edit** - Change condition, notes, value
- **Remove** - Delete from collection
- **Sort** - By artist, title, year, value
- **Filter** - By genre or condition

## Tips for Best Results

### Optimal Image Quality
- 📸 Use clear, well-lit photos
- 🎯 Focus on the album sleeve
- 📐 Keep the record level/straight
- 🚫 Avoid reflections and glare

### Improve Identification
- 📚 Add more images (front + back + spine)
- 💬 Use chat to refine results
- ✏️ Correct any errors in the metadata
- 🔄 Re-analyze with better photos

### Manage Your Collection
- 🏷️ Add personal notes (condition, where bought, etc.)
- 💰 Track estimated values
- 🎵 Organize by genre or decade
- 📊 View collection statistics

## Common Questions

**Q: Why is identification taking so long?**
A: First identification may take 8-10 seconds. Subsequent requests are faster due to caching.

**Q: Can I upload multiple images at once?**
A: Yes! Upload 2-3 images (front/back/spine) for better accuracy.

**Q: How accurate is the identification?**
A: ~85-95% for common records. Less common pressings may need manual adjustment.

**Q: Can I export my collection?**
A: See [User Guide - Collection Management](../user-guide/collection.md) for export options.

## Next Steps

- 📖 Read [User Guide](../user-guide/uploading.md) for detailed features
- 🤖 Learn about [AI Chat](../user-guide/chat.md)
- 💬 Ask questions in the chat interface!

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
- Check [Troubleshooting Guide](../development/setup.md#troubleshooting)
- Search [GitHub Issues](https://github.com/your-username/phonox/issues)
