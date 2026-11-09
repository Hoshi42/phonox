# Phonox Frontend

React + TypeScript + Vite PWA for Phonox vinyl record identification.

## Features

- **Mobile-first navigation**: bottom tab bar on phones, side rail on wide screens (Collection, Capture, Discover, Profile)
- **Collection browsing**: search, sort, grid/list, shelves for recent records, artists and genres
- **Record sheet**: bottom sheet on phones, side drawer on desktop, with focus trapping, Escape and drag-to-dismiss
- **Light and dark theme**: follows the system by default, switchable under Profile
- **Image upload and analysis**: photograph a cover in the Capture tab; results are polled from the backend
- **Progressive Web App**: Installable on mobile and desktop
- **Responsive Design**: Works on desktop, tablet, and mobile

## Quick Start

### Prerequisites

- Node.js 18+
- Backend running on `http://localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
# Start dev server with HMR
npm run dev

# Opens at http://localhost:5173
```

The dev server port and proxy target can be overridden, which is how a branch is previewed next to the regular app:

```bash
PORT=5174 BACKEND_URL=http://localhost:8000 npm run dev
```

### Previewing a branch in isolation

From a git worktree of the branch (so your regular checkout and its running containers are untouched):

```bash
git worktree add ../phonox-preview <branch>
cd ../phonox-preview
docker compose -f docker-compose.preview.yml up -d   # http://localhost:5174
docker compose -f docker-compose.preview.yml down     # when finished
git worktree remove ../phonox-preview
```

The preview reuses the backend and database on port 8000 and installs its own `node_modules` in a Docker volume.

### Build

```bash
# Production build
npm run build

# Preview production build
npm run preview
```

## E2E Testing

```bash
# Run all E2E tests
npm run test:e2e

# Run with UI
npm run test:e2e:ui

# Run specific test file
npm run test:e2e -- e2e/navigation.spec.ts

# Test a preview running on another port
PORT=5174 npm run test:e2e -- e2e/navigation.spec.ts
```

The tests mock the register endpoints (`e2e/support.ts`), so they do not depend on real data.

## Project Structure

```
frontend/
├── src/
│   ├── main.tsx              # Entry point (applies the stored theme before render)
│   ├── App.tsx               # State, API orchestration and tab wiring
│   ├── config.ts             # API base URL
│   ├── styles/               # tokens.css (light/dark design tokens), base.css
│   ├── theme/useTheme.ts     # system | light | dark preference
│   ├── shell/AppShell.tsx    # Tab bar / side rail
│   ├── ui/                   # Sheet, Icon, RecordCard, AnalysisContent
│   ├── views/                # CollectionView, DiscoverView, CaptureView, ProfileView, RecordSheet
│   ├── features/             # collection.ts (filter/sort/group), collectionTools.ts (CSV, analysis)
│   ├── api/ services/        # Backend clients
│   └── components/           # VinylCard, ChatPanel, QuizCard, CollectionMagazine, ErrorModal, VinylSpinner
├── public/
│   ├── manifest.json         # PWA manifest
│   └── sw.js                 # Service worker
├── e2e/
│   ├── navigation.spec.ts    # Tabs, collection, sheet, profile, responsive layout
│   ├── magazine.spec.ts      # PDF magazine panel
│   ├── app.spec.ts           # Smoke tests
│   └── support.ts            # Shared mocks and sample data
├── index.html               # HTML entry point
├── vite.config.ts           # Vite configuration (PORT, BACKEND_URL)
├── tsconfig.json            # TypeScript configuration
└── playwright.config.ts     # Playwright configuration
```

## Theming

All colours come from CSS custom properties in `src/styles/tokens.css`. Use `var(--surface)`, `var(--text)`, `var(--accent)` and the translucent `rgb(var(--ink-rgb) / 0.1)` instead of literal colours so both themes work.

## API Integration

### Backend Endpoints

- `POST /api/v1/identify` - Upload images for analysis
- `GET /api/v1/identify/{record_id}` - Poll for results
- `POST /api/v1/identify/{record_id}/review` - Submit corrections
- `GET /health` - Health check

### Client Usage

```typescript
import { apiClient } from './api/client'

// Upload images
const { id } = await apiClient.identify(files)

// Poll for results
const result = await apiClient.getResult(id)

// Submit corrections
await apiClient.review(id, corrections)
```

## PWA Configuration

### Manifest

- Icon sizes: 192x192, 512x512
- Icons with maskable support for adaptive display
- Standalone display mode (full-screen app)

### Service Worker

- Network-first caching for API calls
- Cache-first for static assets
- Offline support with fallback

### Installation

On supported browsers:
1. Navigate to app
2. Click "Install" in browser menu
3. App installs to home screen

## Environment Variables

Create `.env.local` from the root `.env.example`:

```
VITE_API_URL=http://localhost:8000
VITE_POLL_INTERVAL=2000
VITE_ENV=development
```

For Docker environments, the root `.env` file is automatically loaded.

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 15+
- Mobile browsers (iOS 13+, Android 9+)

## Performance

- TypeScript strict mode enabled
- CSS modules for scoped styling
- Lazy loading with React.lazy
- Service worker caching strategy

## Type Safety

- Full TypeScript strict mode
- Type-safe API client with interfaces
- React component prop typing

## Development

### Code Style

- ESLint-compatible TypeScript
- CSS modules for styling
- React 18 with hooks

### Testing

Playwright E2E tests cover:
- Happy path flow
- Error handling
- Mobile responsiveness
- PWA functionality

## License

© 2026 Phonox. Part of the Phonox vinyl record identification project.
