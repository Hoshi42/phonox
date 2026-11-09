# Managing Your Collection

> **Update (v2.4.0):** Phonox has a new mobile-first interface. The header is gone: navigate with the tab bar (bottom on phones, left rail on larger screens). Record details open in a sheet, and there is a light and a dark theme. See [Navigation](#navigation).

Learn how to manage, organize, and maintain your vinyl collection in Phonox.

## Navigation

| Tab | What it is for |
|---|---|
| **Collection** | Search, sort and browse your records: recently added, artists, genres and all records |
| **Capture** | Chat with the assistant and add records by photographing them (**+ Add Record**) |
| **Discover** | Browse by artist, genre or decade; tapping an entry filters the collection |
| **Profile** | Switch or add profiles, choose light/dark/system theme, collection tools and the [PDF magazine](#pdf-collection-magazine) |

Tapping a record opens its details in a sheet (a side panel on wide screens). Swipe the handle down, press **Esc** or use **✕** to close it. A record that is currently loaded stays reachable from the **Capture** tab through the chip next to its title.

## Collection Overview

The **Collection** tab shows all records saved for the selected profile. You can:
- Search by artist, title, label, catalogue number or barcode
- Sort by artist, title, year, value or date added, and switch between grid and list
- Filter by artist, genre or decade (from the shelves or the **Discover** tab)
- Open a record to view or edit it, move it to another profile or remove it
- Generate analysis reports and export a CSV from the **Profile** tab

## Opening Your Collection

The **Collection** tab is the start screen. The header shows the number of records and their total estimated value; the avatar opens your profile.

When filters or a search are active, the shelves are replaced by a result list with its own total value. Active filters appear as removable chips above the results.

## Viewing Records

### Browse Collection

Each record card shows:
- Album artwork (a placeholder if no image exists)
- Title and artist
- Release year and estimated value

### Switch Profiles

Open **Profile → Switch or add profile** to change between collectors or create a new one. The first time you open Phonox you are asked to choose a profile.

### Search Within Collection

Type in the search field at the top of the Collection tab. The search bar stays visible while you scroll. Use the sort button next to it for sorting and layout.

### Load Record Details

Tap a record to:
- Open the record sheet with full metadata and all images
- Edit fields, add more images, re-analyze and re-estimate the value
- Use **Update in Register** (fixed at the bottom of the sheet) to save changes
- Open Spotify, move the record to another profile or remove it (after confirmation) with the buttons in the sheet header
- Tap **Ask the assistant about this record** to jump straight into the chat with this record as context

## Adding Records

### From Identification Results

After identifying a vinyl record in the **Capture** tab, the result opens in the record sheet:
1. Review the metadata
2. Click **"Add to Register"** at the bottom of the sheet (it saves to the active profile)
3. The record appears in the **Collection** tab

### Adding Images to Existing Records

Once a record is in your collection:
1. Open the record from the **Collection** tab
2. In the sheet, click **"Add More Images"**
3. Select up to 5 images total
4. Images are uploaded to the record
5. Maximum 10MB per image (PNG, JPG, GIF, WebP)

## Managing Records

### Edit Record Metadata

To update a record:
1. Open the record from the **Collection** tab
2. Click **Edit** and change any field:
   - Artist, Title, Year, Label
   - Catalog Number, Barcode
   - Genres, Condition
   - User Notes
3. Click **"Update in Register"** to save changes
4. Changes are persisted to database

### Delete from Collection

To remove a record:
1. Open the record from the **Collection** tab
2. Click the trash button in the sheet header
3. Confirm in the dialog
4. Record is permanently removed from database

**Note:** Deletion cannot be undone. The record data is permanently removed.

### Move to Another Profile

Use the move button in the sheet header to choose an existing profile or create a new one.

### Re-analyze a Record

To improve identification of a saved record:
1. Open the record from the **Collection** tab
2. Click **"Reanalyze All"** (or analyze only new images)
3. System re-processes with updated images
4. Metadata is refreshed

## Collection Reports

**Profile → Collection tools** offers **Analyze collection** (an AI appraisal you can discuss in the chat or download as Markdown) and **Export CSV**. The latest analysis is saved for your profile in the database: afterwards **Open last analysis** shows it again at any time, in any session, without a new AI run; **Run a new analysis** replaces it.

### PDF Collection Magazine

Open the **Profile** tab and expand **PDF Magazine** (section *Collection magazine*). Each collection user can
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

Open **Profile → Collection tools → Analyze collection** to get an AI appraisal of the whole collection. From the result you can continue the conversation in **Capture** (**Chat**) or download it as Markdown (**Report**).

**Export CSV** in the same section downloads every record with its metadata.

## User Management

### Multiple Collectors

Phonox supports multiple users/collectors:
- Each user has their own collection view
- Records are tagged with username
- Switch between collections from the **Profile** tab
- Useful for households or shared collections

### Creating Users

Users are created automatically when:
- Adding a record with a new username
- Typing a new name in **Profile → Switch or add profile**
- No explicit user registration required

### Switching Users

To view another user's collection:
1. Open the **Profile** tab
2. Choose **Switch or add profile**
3. Select the profile; the Collection tab shows that user's records

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
