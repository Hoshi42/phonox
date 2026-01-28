# Changelog

## 1.2.2 (Latest)

- Reduce Tavily search results from 12/6 to 7 for all search functions
- Fix batch image processing in re-analysis: now processes all images (existing + newly uploaded) together
- Fix image display after re-analysis: newly uploaded images now persist to database and appear in UI
- Updated `to_dict()` to include `image_urls` from VinylImage relationships
- Improved image persistence across re-analysis operations

## 1.2.1

- Clean up intermediate analysis, test files, and debug artifacts
- Production ready release

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
