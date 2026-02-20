# Changelog

## [1.9.1] - 2026-02-20 - Spotify URL Fix

### Bug Fixes
- **Fixed Spotify URL Lost on Re-Analysis**
  - `reanalyze` endpoint now parses the `current_record` payload sent by the frontend
  - If the agent graph's `search_spotify_album` call returns nothing (non-deterministic web search), the URL already stored in the current record is preserved as a fallback
  - Previously the URL was silently dropped every time re-analysis ran without a Tavily hit

- **Fixed Spotify Search Parity Between Tavily and DuckDuckGo**
  - DuckDuckGo fallback in `search_spotify_album` previously used the plain query `{artist} {title} spotify album` with no site restriction, so results were dominated by review sites rather than direct Spotify album pages
  - DuckDuckGo now first tries a site-restricted query `{artist} {title} album site:open.spotify.com` (mirrors what Tavily does with `site:spotify.com`)
  - If that returns nothing it falls back to the broader query with `max_results=10`
  - Corrected a misleading log message ("trying broader Tavily search") that actually jumped straight to DuckDuckGo

---

## [1.9.0] - 2026-02-18 - Mobile UI Overhaul & Polish

### New Features
- **Full-Screen Expand/Collapse Panels**
  - Chat and vinyl card panels can expand to full screen on mobile and intermediate views
  - Non-expanded panel is hidden; expanded panel covers entire viewport including header
  - Works across all three breakpoints: desktop (>1200px), intermediate (768-1200px), mobile (<768px)

### Improvements
- **Mobile Responsive Layout**
  - Viewport locked to `100vh` — no page scrolling, all content fits within screen
  - Grid rows use `minmax(0, 1fr)` for strict 50/50 panel split on mobile
  - Container headers stay pinned with flex-shrink: 0
  - Chat input section stays at bottom, textarea scrollbar removed

- **Compact VinylCard Metadata**
  - Inline label-value layout with fixed 80px label width
  - Reduced gaps and font sizes for professional, dense display
  - Edit mode fields properly separated (Artist, Est. Value as individual fields)

- **VinylRegister Mobile Fix**
  - Record cards now match dropdown width on mobile phones
  - Added overflow protection and word-break on long titles/artists
  - Matching horizontal padding between controls and records container

- **Global Scrollbar Styling**
  - Consistent scrollbar appearance across entire app (10px width, rounded thumb)
  - Removed scrollbar arrow buttons for cleaner look
  - Firefox support via `scrollbar-width: thin` and `scrollbar-color`
  - Removed redundant per-component scrollbar styles

- **ChatPanel Header on Mobile**
  - Upload button now visible on mobile (header no longer hidden)
  - Compact padding on smaller screens

### Removed
- **Raw Data Section** removed from VinylCard (toggle and JSON display)

### Technical Details
- 8 files changed across frontend
- Global scrollbar in `index.css` replaces component-specific scrollbar rules
- CSS Modules: `panelHidden` + `mobileExpanded` classes for expand/collapse
- No overlay div — solid background approach eliminates darkening artifacts

---

## [1.8.1] - 2026-02-17 - Backup & Restore Improvements

### Improvements
- **Enhanced Backup & Restore Scripts**
  - Added colored output (cyan) for better readability
  - Progress bars for database restoration and container startup
  - Real-time progress indication during image file copying
  - Shows backup/restore file sizes and timestamps
  - Improved error handling with better feedback messages
  
- **Cleaned Up Script Output**
  - Suppressed Docker warnings about deprecated `version` attribute
  - Hidden PostgreSQL debug messages (SET, CREATE TABLE, etc.)
  - Only relevant status messages displayed
  - Professional, user-friendly output

- **Optimized Image Restoration**
  - Uses efficient tar piping for faster image transfers
  - Verifies file count after copying to ensure completeness
  - Displays total files and size before transfer begins
  - Progress bar completion indication

### Bug Fixes
- **Fixed Image Restore on Raspberry Pi**
  - Images were not being restored due to container timing issues
  - Increased PostgreSQL startup timeout to 60 seconds
  - Containers now fully started before image restoration begins
  - Added proper health checks for backend container

- **Fixed Docker Compose Warnings**
  - Suppressed WARN messages about `version` attribute (no action needed)
  - Cleaner terminal output during backup/restore operations

### Technical Details
- Backup script now extracts images from container volume directly
- Restore script uses tar-to-docker pipeline for efficient 1.5GB+ transfers
- Proper error handling for missing files and failed operations
- Better logging with progress indicators for long operations

---

## [1.8.0] - 2026-02-14 - Web Search Query Optimization

### Improvements
- **Optimized Web Search Query Strategy**
  - Tavily now attempts restricted domain search first (discogs.com, musicbrainz.org, allmusic.com)
  - If restricted search returns 0 results, Tavily retries without domain restrictions
  - DuckDuckGo fallback uses cleaned query (removes special characters, catalog numbers)
  - Eliminates inappropriate DuckDuckGo results by filtering catalog numbers and years
  - Smarter fallback prevents irrelevant content when specific queries fail
  
- **Upgraded DuckDuckGo Library**
  - Migrated from deprecated `duckduckgo-search` to `ddgs>=4.0.0`
  - Eliminates deprecation warnings in logs
  - ddgs package is newer and more reliable
  - Updated imports in websearch.py and web_tools.py

### Bug Fixes
- **Fixed Inappropriate DuckDuckGo Query Results** (#websearch-fallback-quality)
  - DuckDuckGo was returning irrelevant results (dictionary entries, unrelated sites)
  - Root cause: Query contained special characters and non-essential terms
  - Solution: Added `_clean_query_for_fallback()` that sanitizes queries
  - Removes forward slashes, catalog numbers, years from fallback queries
  - DuckDuckGo now receives focused queries: "artist title vinyl record"
  
- **Fixed Tavily Domain Restriction Returning Zero Results** (#tavily-domain-filter)
  - Implemented fallback strategy: restricted search → unrestricted search
  - Prevents search failures when domain filter is too narrow

## Unreleased - Websearch Fallback Reliability

### Bug Fixes
- **Fixed DuckDuckGo Fallback Robustness**
  - Replaced fragile HTML scraping with `duckduckgo-search` library
  - DuckDuckGo now properly bypasses anti-bot measures and rate limiting
  - Library handles HTTP headers and timeouts gracefully
  - Fallback now works reliably when Tavily fails
  
- **Improved Websearch Error Handling**
  - Better logging for debugging search failures
  - Timeouts and connection errors handled gracefully
  - Functions return empty results instead of crashing
  - Proper fallback chain: Tavily → DuckDuckGo → return empty results

### Dependencies
- Added `duckduckgo-search>=3.9.0` to requirements.txt
- Library provides robust web search without API keys

## Unreleased - Previous Websearch Improvements

### Bug Fixes
- **Fixed Tavily API Key Not Being Passed to Client**
  - websearch.py was creating TavilyClient() without api_key parameter
  - Environment variable TAVILY_API_KEY is now properly passed to all TavilyClient instances
  - Fixes "websearch failed" errors that occurred during vinyl identification

- **Added DuckDuckGo Fallback to Agent Websearch**
  - All search functions now fallback to DuckDuckGo if Tavily fails or is unavailable
  - search_vinyl_metadata: Tavily → DuckDuckGo fallback
  - search_vinyl_by_barcode: Tavily barcode search → DuckDuckGo fallback
  - search_spotify_album: Tries both Tavily and DuckDuckGo for album links
  - Deduplicates results from both sources by URL to avoid duplicates
  - DuckDuckGo fallback works even without Tavily API key configured

### Improvements
- Robust websearch with dual-source approach (Tavily primary, DuckDuckGo secondary)
- Better error handling and logging for troubleshooting search failures
- Added imports for BeautifulSoup and requests to support DuckDuckGo HTML parsing
- Search functions now continue gracefully if one method fails, trying alternatives

## 1.7.0 - Mobile-First User Onboarding


### Features
- **Full-Screen User Selection Modal**
  - Complete redesign of first-time user experience
  - Full-screen responsive layout on mobile devices
  - Significantly improved readability on all screen sizes
  
- **Enhanced Mobile Responsiveness**
  - Larger touch targets: 70px button height for better usability
  - Improved typography: 2.5rem title, 1.3rem sections, 1.15rem text
  - Better visual hierarchy and spacing between elements
  - Optimized padding and margins for mobile (1.5rem-2rem)
  
- **Proper Modal Layering**
  - Use React Portals to render modals to document.body
  - Guaranteed z-index positioning above all application overlays
  - Fixes issues with chat panel blocking user selection on first visit
  - modals now: 99999 z-index for guaranteed top layer
  
- **Improved First-Time User Flow**
  - Clear "Your Profiles" section with existing users
  - Intuitive "or" divider between existing and new profiles
  - Better visual feedback with smooth transitions
  - Touch-friendly interface with larger buttons and spacing

### UI/UX Improvements
- Better contrast and readability on mobile devices
- Smooth transitions and hover effects optimized for touch (no hover on mobile)
- Focused input states with glow effect
- Proper button disabled states and styling
- Cleaner mobile viewport usage with full-screen approach

## 1.6.1 - Re-Analysis & Image Management Fixes


### Bug Fixes
- **Fixed Image Duplication on Record Load**
  - Images no longer duplicate when loading registered records into VinylCard
  - Simplified image display logic: only shows `uploadedImages` in UI
  - `image_urls` kept as metadata reference but not displayed to prevent duplication
  - Root cause: was displaying both database URLs and File objects simultaneously

- **Fixed Re-Analysis Status Polling**
  - Changed from ineffective polling mechanism to immediate response
  - Re-analysis endpoint now returns complete analyzed metadata immediately
  - Removed get_identify status endpoint polls for re-analysis (not needed)
  - Fixes "Failed to get re-analysis status" errors

- **Simplified Image Management** 
  - Removed unused `deletedImageUrls` state tracking
  - Deletion now handled directly by removing from `uploadedImages`
  - Single source of truth for image display
  - Cleaner state management in VinylCard.tsx

- **Fixed Spotify URL Deletion on Re-Analysis**
  - Backend: Added missing `spotify_url` and `estimated_value_usd` fields to reanalyze response
  - Spotify URL now properly preserved when re-analyzing records
  - Previously was being dropped because response didn't include the field
  - URL correctly detected by agent graph but wasn't passed through to client

- **Fixed Re-Analyze Button Visibility** 
  - Button now only appears when NEW images are added to a register record
  - No longer shows when just loading a record from register
  - Correctly counts only newly added images (excludes database images)
  - Prevents accidental re-analysis when no new images have been uploaded

### Features
- **Re-Analysis Now Mirrors Upload Flow**
  - Re-analysis includes full web search and market value estimation
  - Results sent to chat panel via `intermediate_results` field
  - User sees search queries, sources, and Claude analysis in chat
  - Same valuation logic as initial identify endpoint (Goldmine weighting)

- **Memory-First Architecture Refinement**
  - Images stay in browser memory until explicit "Update in Register" click
  - Database only touched on explicit user action
  - Loading from register: images fetched as File objects into memory
  - Updated images: only newly added images are uploaded (no re-upload of existing)
  - Metadata updates (condition, value) persist alongside correctly managed images

### Improvements
- **Cleaner Update Logic**
  - VinylCard.handleRegisterAction now uploads all current `uploadedImages`
  - Automatically replaces deleted images in database
  - Combines with metadata updates in single transaction
  - Fixed the "only upload new images" logic that was causing tracking issues

### Files Modified
- `frontend/src/components/VinylCard.tsx` - Image display and state management
- `frontend/src/App.tsx` - Image loading from register, kept `image_urls` as reference
- `backend/api/routes.py` - Re-analysis endpoint returns immediate response with intermediate results
- `backend/agent/graph.py` - Removed LangGraph MemorySaver checkpointer (prevents recursion)

---

## 1.6.0 - Multi-Image Intelligence & Condition Detection

### Major Features
- **LLM-Based Metadata Aggregation** 🤖
  - Replaced complex rule-based aggregation with Claude-powered intelligent merging
  - Automatically resolves conflicts between multiple image analyses
  - Normalizes capitalization ("PINK FLOYD" → "Pink Floyd")
  - Merges barcodes, catalog numbers, and genres intelligently
  - Provides reasoning for aggregation decisions
  - ~75% reduction in code complexity (170 lines → 40 lines)
  - New environment variable: `ANTHROPIC_AGGREGATION_MODEL` (default: claude-sonnet-4-5-20250929)

- **Condition Assessment** 🔍
  - Automatic vinyl condition detection from images
  - Uses Goldmine grading scale (M, NM, VG+, VG, G+, G, F, P)
  - Conservative multi-image approach (uses worst condition seen)
  - Condition notes with visible wear descriptions
  - Condition badge in UI with color coding
  - Condition multiplier affects value calculations
  - Integrated into aggregation and enhancement workflows

- **Advanced Retry Logic** 🔄
  - Exponential backoff for transient API failures (1s → 2s → 4s)
  - Up to 3 retry attempts per image
  - Handles timeouts, rate limits, and temporary unavailability
  - Detailed retry logging with attempt tracking
  - Image-specific error reporting
  - Graceful fallback to simple merge when LLM fails

- **Image-Context Aware Prompts** 🎯
  - Image 1 optimized for artist/title extraction
  - Images 2+ optimized for barcode/catalog/genres
  - Context-aware prompts reference previous results
  - Better multi-image coordination
  - Reduced duplicate analysis
  - Higher accuracy with focused instructions

### Model Configuration Management
- **Centralized Model Configuration**
  - All Claude models configurable via environment variables
  - `ANTHROPIC_VISION_MODEL`: Image analysis (default: claude-sonnet-4-5-20250929)
  - `ANTHROPIC_CHAT_MODEL`: Chat responses (default: claude-haiku-4-5-20251001)
  - `ANTHROPIC_AGGREGATION_MODEL`: Multi-image merging (default: claude-sonnet-4-5-20250929)
  - `ANTHROPIC_ENHANCEMENT_MODEL`: Metadata enrichment (default: claude-opus-4-1-20250805)
  - All models documented in `.env.example` with alternatives
  - Cost optimization strategies documented
  - Easy switching between model tiers

### Bug Fixes
- **Fixed f-string Format Specifier Errors**
  - Properly escaped JSON examples in prompts with `{{}}` and `{{{{}}}}`
  - Fixed "Invalid format specifier" errors during vision extraction
  - Affected files: `graph.py`, `vision.py`, `metadata_enhancer.py`
  - All multi-image analysis now works correctly

### Improvements
- **Metadata Quality Validation**
  - Validates confidence thresholds
  - Checks for placeholder values (Unknown, N/A, ERROR)
  - Validates year range (1900-2026)
  - Warns about missing genres
  - Validates barcode format (12-13 digits)
  - Quality issues logged and tracked

- **Enhanced Confidence Scoring**
  - Updated weights: Discogs 40%, MusicBrainz 20%, Vision 18%, WebSearch 12%
  - Added Image (5%) and User Input (5%) sources
  - Better reflects reliability of each source
  - More accurate confidence calculations

### Documentation
- **New Documentation Files**
  - `LLM_AGGREGATION_APPROACH.md`: Why and how LLM aggregation works
  - `MODEL_CONFIGURATION.md`: Complete model configuration guide
  - `METADATA_DETECTION_ANALYSIS.md`: Technical analysis of multi-image issues
  - `METADATA_DETECTION_IMPLEMENTATION.md`: Implementation details
  - `METADATA_DETECTION_QUICKSTART.md`: Quick reference guide
  - `IMPROVEMENTS_IMPLEMENTED.md`: Summary of all improvements
  - `TESTING_GUIDE_IMPROVEMENTS.md`: Testing procedures

### Cost Analysis
- **Per 2-Image Upload** (with new aggregation):
  - Vision analysis: $0.008 (2 × $0.004)
  - LLM aggregation: $0.001
  - **Total: $0.009** (12.5% increase, worth it for intelligence gain)
- Condition extraction: included in vision analysis (no extra cost)
- Enhancement: $0.003 when adding images to existing records

### Verification
- ✅ Multi-image uploads work without f-string errors
- ✅ LLM aggregation merges metadata intelligently
- ✅ Retry logic handles transient failures
- ✅ Image-specific prompts improve accuracy
- ✅ Condition detected and displayed in UI
- ✅ All model configurations via environment variables
- ✅ Quality validation catches suspicious data
- ✅ Backend starts without errors

## 1.5.3

### Critical Bug Fixes
- **Fixed Image Upload UnicodeDecodeError**
  - Added custom `RequestValidationError` handler to prevent encoding binary file data as UTF-8
  - Prevents `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x89...` when uploading PNG/JPEG files
  - Error responses now only include sanitized error metadata (location, type, message)

- **Enhanced Image Upload Endpoint**
  - `POST /api/register/images/{record_id}` now has comprehensive error handling
  - File size validation (max 10MB per file)
  - Empty file detection
  - Content-type validation for image files
  - Individual error reporting per file (one file error doesn't block others)
  - Proper database transaction management with rollback on failure
  - Better error messages returned to frontend

### Verification
- ✅ Image uploads succeed without UnicodeDecodeError
- ✅ Images saved to database and disk
- ✅ Images visible in register list view
- ✅ Images displayed on vinyl card detail view
- ✅ Proper error handling for invalid files
- ✅ Multi-file uploads partially succeed if some files fail

## 1.5.2

### Critical Bug Fixes
- **Fixed CORS Headers Blocking Frontend-Backend Communication**
  - Removed interfering debug middleware that prevented CORS header propagation
  - Simplified and verified CORS configuration for all origins
  - Ensures `Access-Control-Allow-Origin: *` is properly returned
  - All cross-origin requests from frontend now work correctly

- **Fixed 500 Error on Chat Endpoint**
  - Removed duplicate `get_db()` function in routes.py
  - Fixed `TypeError: 'NoneType' object is not callable` 
  - Now properly imports initialized get_db from database module
  - Chat endpoint (record-specific and general) fully operational

- **Web Search Performance Optimization**
  - Reduced URL scraping timeout from 10s to 5s
  - Reduced scraped URLs per search from 2 to 1
  - Improved error handling with automatic DuckDuckGo fallback
  - `/web` command now responds within acceptable timeframe (25-40s)

- **Web Scraping Configuration (NEW)**
  - **`WEB_SCRAPING_TIMEOUT`**: Configurable timeout per URL (default: 10s)
  - **`WEB_SCRAPING_MAX_URLS`**: Configurable URLs per search (default: 3)
  - Full environment variable support for deployment flexibility
  - Tuning recommendations in `.env.example` for different scenarios
  - Configuration logged on startup for verification

### Verification
- ✅ All health checks passing
- ✅ CORS headers properly returned
- ✅ Database queries working
- ✅ Chat endpoint fully functional
- ✅ Update/Web Search buttons operational
- ✅ Web search with `/web` command working

## 1.5.1

### Database Connection & Infrastructure
- **Automatic Database Retry Logic**: Added robust connection retry mechanism with exponential backoff
  - Configurable retry attempts (default: 5)
  - Exponential backoff delays: 2s → 4s → 8s → 16s → 30s
  - Comprehensive error alerting with troubleshooting steps
  - Critical alerts log when max retries exceeded
  - Connection pooling with pre-ping and recycling
  - Masked URLs in logs for security
  - Graceful HTTP 503 responses when DB unavailable

- **Enhanced CLI Installation**: Improved `install` command with detailed progress feedback
  - Step-by-step progress indicators
  - Database health verification during setup
  - Clear access instructions after installation
  - Better error messages and guidance

- **CLI Documentation Command**: New `docs` command to start MkDocs server locally
  - Automatic virtual environment detection and creation
  - Uses existing .venv if available
  - Automatically installs mkdocs from requirements
  - Serves documentation at http://localhost:8001

### Environment Configuration Consolidation
- **Unified .env Configuration**: All environment variables centralized in root `.env.example`
  - Consolidated backend, frontend, and database settings
  - Database retry configuration fully documented
  - Frontend polling and UI settings included
  - Single source of truth for all configuration
  - Removed duplicate frontend/.env.example

- **Documentation Updates**:
  - Added comprehensive environment variables table in README
  - Installation guide includes all configuration options
  - Database retry settings documented with examples
  - Frontend configuration options explained

### Documentation Improvements
- **New User Guides** (3 comprehensive guides):
  - Uploading Records: Image upload best practices, identification workflow
  - Managing Collection: Collection organization, bulk operations, backups
  - Chat Features: AI capabilities, query examples, web search integration

- **Enhanced Installation Guide**: Complete environment setup with retry configuration
- **Database Troubleshooting Guide**: Connection issues, retry examples, debugging tips
- **Updated MkDocs Navigation**: Cleaned up structure, added troubleshooting section
- **CLI Documentation**: All commands, usage examples, venv detection explained

### Code Quality
- **Improved CLI Design**: Better user feedback with styled progress messages
- **Virtual Environment Detection**: Intelligent .venv detection before global installs
- **Database Connection Manager**: New `backend/db_connection.py` module with:
  - DatabaseConnectionManager class for robust connection handling
  - Retry logic with configurable parameters
  - Health check integration
  - Logging and alerting system

### Bugfix
- **Frontend Environment Cleanup**: Removed redundant frontend/.env.example

## 1.5.0

### Collection Analysis & ChatPanel Integration
- **Professional Collection Analysis**: Added "Estimate Complete Collection" feature with AI-powered analysis
  - Compiles collection statistics (genres, decades, conditions, top artists)
  - Sends to Claude for professional appraisal-style insights
  - Displays formatted analysis with markdown support and tables
  - Download analysis reports as markdown files
- **ChatPanel Integration**: New button to send collection analysis to chat as context
  - Seamlessly switch from register to chat with analysis pre-loaded
  - Analysis appears as styled context message in ChatPanel
  - Continue discussion about collection insights with AI

### Data Export & Storage Improvements
- **CSV Export Refinements**: 
  - Changed delimiter from comma to semicolon for better European compatibility
  - All fields exported as text format (prevents formula interpretation)
  - European decimal formatting (comma-based)
  - Barcode field prefixed with apostrophe to force text in spreadsheets
  - Removed notes field from exports (chat entries no longer stored)
- **Chat Storage Fix**: Fixed database pollution where chat messages were being stored in user_notes
  - Chat is now purely ephemeral
  - CSV exports clean and data-focused

### UI/UX Enhancements
- **VinylSpinner Integration**: Unified loading spinner using phonox.png across collection analysis
- **Analysis Modal**: Professional styled modal with download and chat buttons
- **System Messages**: New styled context messages for rich markdown content in chat


## 1.4.2

### Docker & CLI Improvements
- **Docker Network Recovery**: Fixed network connectivity issues after Docker updates with automatic recovery on restart
- **CLI Health Checks**: Added network and database health monitoring to CLI
- **CLI Network Status**: Display Docker network status in main menu alongside containers and backups
- **CLI Restart Command**: New `restart` command with automatic network recovery (Option 6 in menu)

### Register UI & UX Enhancements
- **Error Modal**: Replaced browser alert with stylized, centered error modal matching app design
  - Auto-dismiss after 5 seconds or manual close
  - Gradient background and blur effect
  - Better visibility and UX
- **Image Management**: Simplified image deletion flow
  - Deleted images removed from memory, not sent to backend
  - Backend overwrites image list on update (cleaner approach)
  - Deleted images properly persisted to database
- **Update Indicator**: Added pulsing button with loading spinner during register update
  - Shows "Updating..." text with rotating ⚙️ icon
  - Button disabled during update (prevents double-clicks)
  - Visual feedback for long-running operations


## 1.4.1

### Architecture & Backend Optimization
- **In-Memory Analysis**: Refactored `/reanalyze` endpoint to work entirely in-memory without database dependencies
  - Frontend sends current record data with new images
  - Backend processes in-memory and returns merged metadata
  - Database only involved when user explicitly saves to register
  - Eliminates 500 errors on re-analysis of unsaved records
  - Significantly faster analysis without DB queries

### Condition Field Improvements
- **Agent-Only Condition**: Removed all `getCondition()` fallbacks - condition now exclusively from agent's image analysis
  - No longer calculated from confidence score
  - Shows "Not analyzed" if agent didn't provide condition
  - Only persists to database when user saves to register
- **Analysis Message Enhancement**: Added condition suggestion to "Analysis Complete" message in chat
- **Edit Display Fix**: Condition field now correctly shows saved value when editing (not just "Good" default)


## 1.4.0

### Documentation Site
- Added professional MkDocs documentation site with Material theme
- Comprehensive documentation structure: Getting Started, User Guide, API Reference, Architecture, Development, Deployment
- Interactive navigation with dark mode toggle and built-in search
- Complete API documentation with endpoints, authentication, and code examples
- Contributing guidelines and project information
- Phonox logo integration in documentation header
- Ready for deployment to GitHub Pages, Cloud Run, or Netlify

## 1.3.2

### Documentation
- Added `.env.example` template with all environment variables documented
- Includes placeholder values and helpful comments for configuration
- Links to API key sources (Anthropic, Tavily)
- Examples for different deployment environments (local, Docker, production)

## 1.3.1

### Cleanup
- Removed 14 temporary development documentation files
- Project structure cleaned up for open source release

## 1.3.0

### Mobile UI Improvements
- Optimized ChatPanel layout on mobile: increased message width from 85% to 95%, reduced padding for better readability
- Improved mobile header layout: kept all items on single row (Logo + Title + User Info + Register Button)
- Fixed ChatPanel container height on mobile: increased from 50vh to 65vh for better conversation visibility
- Changed quick action buttons to 2-column grid layout on mobile for better organization
- Unified button styling across header: aligned UserManager and Register Button heights, border-radius, and font sizes
- Adjusted padding consistency: ChatPanel, header, and main content all use 12px horizontal padding on mobile
- Fixed button overflow: Register Button now fits properly on mobile screens with responsive sizing
- Optimized spacing for touch targets while maintaining visual consistency

## 1.2.3

- Unified spinner behavior across all analyses (upload, re-analysis, value estimation)
- Consistent glass-morphism overlays with semi-transparent backgrounds and blur effects
- Updated VinylSpinner text colors to work with dark theme overlays
- All loading states now use same visual design system with centered VinylSpinner
- Customizable spinner messages for different analysis types

## 1.2.2

- Reduce Tavily search results from 12/6 to 7 for all search functions
- Fix batch image processing in re-analysis: now processes all images (existing + newly uploaded) together
- Fix image display after re-analysis: newly uploaded images now persist to database and appear in UI
- Updated `to_dict()` to include `image_urls` from VinylImage relationships
- Improved image persistence across re-analysis operations

## 1.2.0

- Fix white screen issue and integrate ChatPanel messaging
- Enhanced frontend stability and chat integration

## 1.1.0

- Add Condition field UI
- Integrate value estimation features
- Optimize CLI performance

## 1.0.0 (2026-01-25)

- Added Spotify URL support end-to-end:
  - Backend DB: `vinyl_records.spotify_url` column
  - API models: `spotify_url` in `VinylMetadataModel`, `ReviewRequest`, and register endpoints
  - Register add/update now persist `spotify_url`
  - Frontend types and UI: edit/display in Vinyl card; 🎧 icon in register and card header
- Enhanced websearch with DuckDuckGo fallback alongside Tavily
  - Combined results with deduplication; logging markers confirm DDG usage
- Version bump to `1.0.0` in backend app and health/root endpoints
- Minor UI polish for list/grid register views

## Previous

- 0.3.x: Initial identification, register, and chat features
