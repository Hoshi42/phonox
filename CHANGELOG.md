# Changelog

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
