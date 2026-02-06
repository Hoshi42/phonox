# Changelog

See [CHANGELOG.md](../../CHANGELOG.md) for detailed version history.

All notable changes to Phonox are documented here.

## Versioning

Phonox uses semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes

## Versions

### v1.5.3 (Current)

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

---

[View full changelog →](../../CHANGELOG.md)
