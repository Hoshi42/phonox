# Changelog

All notable changes to Phonox are documented here.

## Versioning

Phonox uses semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes

## Versions

### v1.9.1 (Current) - 2026-02-20

**Spotify URL Fix**

- **Re-analysis now preserves existing Spotify URL**: the `reanalyze` endpoint parses the `current_record` payload sent by the frontend and uses the stored URL as a fallback when the agent graph's Spotify web search returns nothing (non-deterministic)
- **DuckDuckGo Spotify search parity with Tavily**: previously DDG used a plain query (`{artist} {title} spotify album`) with no site restriction, resulting in a near-zero hit rate for direct album links; it now first tries `site:open.spotify.com` (matching Tavily's `site:spotify.com` strategy), then falls back to the broader query
- Fixed misleading log message ("trying broader Tavily search") that was actually jumping straight to DuckDuckGo

### v1.9.0 - 2026-02-18

**Mobile UI Overhaul & Polish**

- Full-screen expand/collapse panels for chat and vinyl card on mobile/intermediate views
- Viewport locked to 100vh — no page scrolling, content fits within screen
- Compact VinylCard metadata with inline label-value layout (80px fixed labels)
- VinylRegister record cards now match dropdown width on mobile
- Global scrollbar styling: consistent 10px rounded thumb, no arrow buttons, Firefox support
- ChatPanel Upload button now visible on mobile
- Removed Raw Data section from VinylCard
- Edit mode fields properly separated (Artist, Est. Value as individual fields)
- Overflow protection and word-break on long titles/artists in register

### v1.8.1 - 2026-02-17

**Backup & Restore Improvements**
- Enhanced backup and restore scripts with colored output (cyan)
- Added progress bars for database restoration and container startup
- Real-time progress indication during image file copying
- Shows backup/restore file sizes and timestamps
- Improved error handling with better feedback messages
- Fixed image restore on Raspberry Pi (increased PostgreSQL startup timeout)
- Suppressed Docker warnings about deprecated `version` attribute
- Optimized image restoration using efficient tar piping
- Verifies file count after copying to ensure completeness

### v1.8.0 - 2026-02-14

**Web Search Query Optimization**
- Optimized Tavily search strategy: tries restricted domain search first, then unrestricted fallback
- Upgraded to ddgs>=4.0.0 (from deprecated duckduckgo-search)
- Fixed inappropriate DuckDuckGo results by sanitizing queries (removes special chars, catalog numbers)
- Smarter fallback prevents irrelevant content when specific queries fail
- Eliminated deprecation warnings in logs

### v1.7.0

**Mobile-First User Onboarding**
- Full-screen user selection modal with improved mobile responsiveness
- Larger touch targets (70px buttons) for better usability
- Proper modal layering with React Portals (z-index 99999)
- Fixed issues with chat panel blocking user selection on first visit
- Better visual hierarchy and spacing optimized for mobile devices

### v1.6.1

**Re-Analysis & Image Management Fixes**
- Fixed image duplication when loading registered records
- Fixed re-analysis status polling (now returns immediate response)
- Fixed Spotify URL deletion on re-analysis
- Re-analysis now mirrors upload flow with full web search
- Memory-first architecture: images stay in browser until explicit update
- Simplified image management with single source of truth

### v1.6.0

**Multi-Image Intelligence & Condition Detection**
- LLM-based metadata aggregation replaces rule-based system (~75% code reduction)
- Automatic vinyl condition detection using Goldmine grading scale
- Advanced retry logic with exponential backoff (up to 3 attempts)
- Image-context aware prompts optimized per image position
- Condition multiplier affects value calculations

### v1.5.3

**Critical Bug Fixes**
- Fixed Image Upload UnicodeDecodeError when uploading PNG/JPEG files
- Added custom RequestValidationError handler to prevent binary data encoding
- Enhanced POST /api/register/images/{record_id} endpoint with comprehensive validation
- File size validation (max 10MB), empty file detection, content-type validation
- Individual error reporting per file with proper database transaction management

### v1.5.2

**Critical Bug Fixes**
- Fixed CORS headers blocking frontend-backend communication
- Fixed 500 error on chat endpoint (duplicate get_db)
- Optimized web search performance with timeout reductions
- All endpoints verified and working

### v1.5.1

**Database & Infrastructure**
- Automatic database connection retry with exponential backoff
- Configurable retry settings (attempts, delays)
- Comprehensive error alerting and troubleshooting
- New CLI `docs` command to view documentation locally
- Virtual environment detection and management

**Environment Configuration**
- Unified .env configuration (all variables in one place)
- Environment variables fully documented in README
- Database retry configuration with examples
- Frontend configuration options explained

**Documentation**
- 3 new user guides (uploading, collection management, chat)
- Enhanced installation guide with all options
- Database troubleshooting guide
- Cleaned up MkDocs navigation structure

### v1.5.0

**Collection Analysis & ChatPanel Integration**
- Professional collection analysis feature
- ChatPanel integration for analysis
- CSV export refinements for European compatibility
- Unified loading spinner
- Analysis modal with download button

### v1.4.2

**Image Handling**
- Fixed batch image processing
- Improved image persistence
- Better image display after re-analysis

### v1.2.0

**Chat Integration**
- ChatPanel messaging
- Web search fallback
- Improved stability

### v1.1.0

**Features**
- Condition field
- Value estimation
- CLI performance optimization

### v1.0.0

**Release**
- Spotify URL support
- DuckDuckGo fallback
- Collection management
- Chat interface
