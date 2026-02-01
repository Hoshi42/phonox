# Managing Your Collection

Learn how to manage, organize, and maintain your vinyl collection in Phonox.

## Collection Overview

The **Collection** panel shows all your saved records. You can:
- View all records with thumbnails
- Search and filter records
- Sort by artist, title, year, or value
- Edit record details
- View statistics

## Viewing Records

### Browse Your Collection

1. Click **"Collection"** tab
2. See thumbnails of all your records
3. Scroll to view more

### Search Records

Use the search bar to find:
```
Search for:
- Artist name: "The Beatles"
- Album title: "Abbey Road"
- Year: "1969"
- Label: "Apple"
```

### Sort & Filter

**Sort by:**
- Artist (A-Z)
- Title (A-Z)
- Year (oldest first)
- Value (highest first)
- Date added (newest first)

**Filter by:**
- Condition (poor/fair/good/excellent/near mint)
- Genre
- Decade
- Collector tag

## Editing Record Details

### View Full Details

Click any record to see:
- Album artwork
- Complete metadata
- Current value
- Your notes
- Edit button

### Edit Information

Click **"Edit"** to modify:

**Metadata:**
- Artist name
- Album title
- Release year
- Label name
- Catalog number

**Personal Info:**
- Condition (select from dropdown)
- Your notes/comments
- Estimated value (your assessment)
- Personal rating (1-5 stars)
- Spotify link (paste URL)

**Collector Info:**
- Collector tag (your identifier)
- Date acquired
- Where purchased
- Purchase price

### Save Changes

Review changes and click **"Save"**

## Removing Records

### Delete from Collection

1. Open record details
2. Click **"Delete"** button
3. Confirm deletion

**Note:** This cannot be undone. Your record history is deleted.

## Collection Statistics

View insights about your collection:

- **Total Records**: Number of albums
- **Total Value**: Sum of all estimated values
- **Average Value**: Mean value per record
- **By Condition**: Breakdown of conditions
- **By Genre**: Genre distribution
- **By Decade**: Records by release decade
- **By Condition**: Records by physical condition

## Exporting Data

### Export Collection

Export your collection as:
- **CSV** - Spreadsheet format
- **JSON** - Machine-readable format
- **PDF** - Printable format

Use for:
- Insurance documentation
- Backups
- Analysis
- Sharing with friends

## Backup & Recovery

### Automated Backups

Phonox automatically backs up your collection:
- Daily snapshots
- Stored in `./backups/` folder
- Kept for 7 days

### Manual Backup

```bash
./phonox-cli backup
```

### Restore from Backup

```bash
# List available backups
ls -lh backups/

# Restore specific backup
./phonox-cli restore 20260201_120000
```

## Collection Best Practices

### Keep Information Accurate

- Update condition as records age
- Note any damage or repairs
- Track purchases and sales
- Update values periodically

### Add Detailed Notes

Include:
- Pressing information (country, year)
- Condition notes (scratches, etc.)
- Grading (Mint/Near Mint/Very Good/etc.)
- Purchase details
- Seller/source information

### Monitor Values

- Check market prices periodically
- Update estimated values
- Track appreciation/depreciation
- Review for insurance purposes

### Organize Logically

Use collector tags for:
- Genre
- Decade
- Series (e.g., "Pink Floyd Collection")
- Quality tier (investment/casual)
- Display location

## Bulk Operations

### Edit Multiple Records

1. Select multiple records (checkboxes)
2. Click **"Bulk Edit"**
3. Choose fields to update:
   - Condition
   - Genre
   - Collector tag
4. Apply changes

### Export Multiple Records

Select records and export to:
- CSV for spreadsheet
- JSON for processing
- PDF for printing

## Sharing Your Collection

### Share Collection Links

Generate shareable link (optional):
1. Click **"Share"** button
2. Choose privacy level:
   - Private (only you)
   - Unlisted (anyone with link)
   - Public (visible in Phonox)
3. Copy and share link

### Hide Sensitive Info

Choose what to share:
- Show/hide values
- Show/hide personal notes
- Show/hide condition details

## Collection Goals

Track collecting goals:

- **Target Records**: Records you want
- **Budget**: Monthly collecting budget
- **Completion**: Percentage of artist/label completion
- **Value Target**: Target collection value

## Troubleshooting

**Can't find a record:**
- Use search function
- Check sorting/filters
- Record may not be saved yet

**Can't edit values:**
- Ensure you're in Edit mode
- Check for validation errors
- Fields may be read-only

**Backup missing:**
- Check `./backups/` folder
- Run manual backup
- Verify database connection

## Next Steps

- [Chat with your collection](./chat.md)
- [Get valuations](./valuation.md)
- [Setup backup schedule](../database-retry.md)
