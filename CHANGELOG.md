# Changelog

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
