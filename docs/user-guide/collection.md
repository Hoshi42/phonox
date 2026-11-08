# Managing Your Collection
> **Update (v2.0.5):** The user switcher in the header is now a compact dropdown in all views. The My Register button height is aligned with the other header controls on mobile.

> **Update (v1.9.6):** The VinylRegister modal now uses a taller layout and vertical scrolling, ensuring all records and action buttons (like 'Add to Register' and 'Update') are always visible, even with large collections.

Learn how to manage, organize, and maintain your vinyl collection in Phonox.

## Collection Overview

The **My Collection** feature stores all your saved vinyl records in a PostgreSQL database. You can:
- View all records with thumbnails
- Filter by user/collector
- Load records back into VinylCard for viewing/editing
- Delete records from your collection
- Generate analysis reports

## Opening Your Collection

Click the **"My Collection"** button (top right) to open the VinylRegister modal.

The register displays:
- **User selector** - Filter by username/collector
- **Record list** - All saved records with thumbnails
- **Record count** - Total records for selected user
- **Action buttons** - View, Delete, Report

## Viewing Records

### Browse Collection

The register shows each record with:
- Album artwork thumbnail (if available)
- Artist name
- Album title
- Release year
- User/collector name
- Date added to collection

### Filter by User

Use the user dropdown menu to:
- View only your records
- Switch between different collectors
- See records from specific users

### Search Within Collection

While viewing the register:
- Scroll through the list of records
- Records are sorted by creation date (newest first)
- Each record shows key identifying information

### Load Record Details

Click the **"View"** button on any record to:
- Close the register modal
- Load the complete record into VinylCard
- Display full metadata and all images
- Enable editing and value estimation
- Add more images to the record

## Adding Records

### From Identification Results

After identifying a vinyl record:
1. Review the metadata in VinylCard
2. Select your username from the dropdown (or type a new username)
3. Click **"Add to Register"** button
4. Record is saved with current date/time
5. Confirmation message appears

### Adding Images to Existing Records

Once a record is in your collection:
1. Load the record from the register (click "View")
2. In VinylCard, click **"Add Image"** button
3. Select up to 5 images total
4. Images are uploaded to the record
5. Maximum 10MB per image (PNG, JPG, GIF, WebP)

## Managing Records

### Edit Record Metadata

To update a record:
1. Load the record from register (click "View")
2. In VinylCard, click on any field to edit:
   - Artist, Title, Year, Label
   - Catalog Number, Barcode
   - Genres, Condition
   - User Notes
3. Click **"Update in Register"** to save changes
4. Changes are persisted to database

### Delete from Collection

To remove a record:
1. In the register, find the record
2. Click **"Delete"** button next to the record
3. Confirm deletion in the prompt
4. Record is permanently removed from database

**Note:** Deletion cannot be undone. The record data is permanently removed.

### Re-analyze a Record

To improve identification of a saved record:
1. Load the record from register
2. Click **"Re-analyze"** button
3. Upload new/additional images
4. System re-processes with updated images
5. Metadata is refreshed

## Collection Reports

### PDF Collection Magazine

Open **My Register**, then expand **PDF Magazine**. Each collection user can
have one magazine. It is an English, A4 **landscape** PDF with:

- A title page, editable foreword and linked contents/PDF bookmarks.
- **One half page per album**, two per page, with the photographs of that copy, the key facts and the estimated value.
- A half-page artist portrait before an artist's records, where portrait text exists.
- EUR estimates, dated when the valuation date is known.

Information that is not available is simply left out of the PDF: no portrait page, no empty fields,
no "unknown" placeholders. Text that is too long for a half page is shortened with an ellipsis
(the draft warnings tell you which). Images are resampled to the printed size, which keeps even
large collections to a moderate file size.

Set a title, subtitle, optional display name and optional cover photograph.
Leave the initial foreword empty for a factual proposal. Private collector notes
are excluded unless explicitly enabled.

**Research and cost consent:** available Discogs, MusicBrainz and web search
sources are used after you approve the external data transfer and cost allowance.
Only necessary artist/album/release details leave Phonox, not your name, private
notes or photographs. Each job has 20 research/AI steps and at most 1,200 output
tokens per AI call. The displayed EUR allowance is approximate, not a provider
quote. You can disable research to create a magazine from stored information.
Missing API keys or failed sources are shown as warnings.

Click **Prepare magazine**, wait for the draft, then review and edit the foreword,
artist portraits, artist chapter assignments and record descriptions.
**Save editorial changes** refreshes chapter structure. Once reviewed, select
**Approve & create PDF**. The PDF uses embedded fonts and images and can be read
offline.

**Open magazine** and **Download PDF** reopen the stored edition without
generation or API costs, including in later sessions. After adding records,
the panel displays new/changed/removed counts. **Update magazine / prepare draft**
creates a new snapshot, inserts records into the appropriate artist chapters
and rebuilds contents, page numbers and summaries. It also handles changed or
removed records. Previously edited text/settings are retained; an automatic
foreword updates its counts. Unfinished research can continue within a new,
explicitly approved job budget.

Enable **Research current EUR estimates** when you want new valuations.
Reused prices retain their real dates; an edition's creation date is not a
valuation date. Missing values do not count as zero, and estimates are not
binding sale prices or insurance appraisals.

The previous PDF remains available during an update and after cancellation or
failure. It is replaced only after successful creation. Following a server
restart, explicitly retry interrupted work; already incurred costs remain.
The current PDF is kept until replacement or **Delete magazine**, which does
not delete your records. Only the latest successful edition is offered, not a
full version archive.
Users with a saved magazine remain in the user selector even if their collection
becomes empty.

### Generate Analysis Report

Click **"Generate Report"** in the register to:
- Create a comprehensive collection analysis
- Export record list with metadata
- View statistics and insights
- Get valuation summaries

Report includes:
- Total record count
- Records by user
- Date ranges
- Metadata completeness

## User Management

### Multiple Collectors

Phonox supports multiple users/collectors:
- Each user has their own collection view
- Records are tagged with username
- Filter collection by user
- Useful for households or shared collections

### Creating Users

Users are created automatically when:
- Adding a record with a new username
- Typing a new name in the user selector
- No explicit user registration required

### Switching Users

To view another user's collection:
1. Open register
2. Select user from dropdown
3. Register updates to show that user's records

## Database & Backups

### Automatic Database Storage

All records are stored in PostgreSQL with:
- Full metadata persistence
- Image file references
- User associations
- Timestamps (created_at, updated_at)

### Database Backups

Phonox includes backup functionality:
- Backups stored in `./backups/` directory
- Manual backup via command line
- Backup includes all records and images

**Manual Backup:**
```bash
# From project root
cd /home/hoshhie/phonox
./scripts/backup.sh
```

**Restore from Backup:**
```bash
# List available backups
ls -lh backups/

# Restore specific backup
./scripts/restore.sh backups/phonox_db_YYYYMMDD_HHMMSS.sql
```

### Docker Database

If running via Docker:
- Database is in the `db` container
- Data persisted in Docker volume
- Backups should be done regularly

See [Database Retry Guide](../database-retry.md) for troubleshooting database connections.

## Best Practices

### Keep Metadata Accurate

- Update condition as records age
- Add detailed notes about pressing variants
- Include catalog numbers when known
- Tag records with correct user/collector

### Image Management

- Upload clear, well-lit photos
- Include front and back covers
- Add label photos for pressing details
- Keep images under 10MB per file

### Organize by User

Use different usernames for:
- Different household members
- Different collections (e.g., "jazz_collection", "rock_collection")
- Gift records vs. purchased
- Display vs. storage records

### Check Current Values

- Use **"Check Current Value"** to get market prices
- Update periodically for insurance
- Track appreciation over time
- Values in both EUR and USD

## Troubleshooting

### Can't See My Records

- Check user filter - ensure correct user selected
- Verify record was saved (look for confirmation message)
- Check database connection (see top-right status indicator)
- Refresh the page

### Images Not Loading

- Check uploads/ directory has files
- Verify file paths in database
- Ensure images are under 10MB
- Try uploading images again

### Duplicate Records

- Use "View" to check before adding duplicates
- Compare catalog numbers and barcodes
- Delete unwanted duplicate manually
- Consider different pressings/editions

### Database Connection Issues

See [Database Retry Documentation](../database-retry.md) for:
- Connection troubleshooting
- Automatic retry configuration
- PostgreSQL setup
- Docker networking

## Next Steps

- [Learn about Chat features](./chat.md)
- [Upload new records](./uploading.md)
- [API Reference](../api/endpoints.md)
