# Phonox Frontend

React + TypeScript + Vite PWA for Phonox vinyl record identification.

## Features

- **Image Upload**: Drag-and-drop interface for 1-5 images
- **Real-time Analysis**: Polls backend for AI identification results
- **Manual Review**: Correction form for low-confidence results
- **Progressive Web App**: Installable on mobile and desktop
- **Offline Support**: Service worker caches results
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
npm run test:e2e -- e2e/app.spec.ts
```

## Project Structure

```
frontend/
├── src/
│   ├── main.tsx              # Entry point
│   ├── App.tsx               # Main app component
│   ├── App.css               # Global styles
│   ├── api/
│   │   └── client.ts         # API client (fetch-based)
│   └── components/
│       ├── ImageUpload.tsx   # Image upload component
│       ├── LoadingSpinner.tsx # Loading indicator
│       ├── ResultsView.tsx    # Results display
│       ├── ReviewForm.tsx     # Manual correction form
│       └── *.module.css       # Component styles
├── public/
│   ├── manifest.json         # PWA manifest
│   └── sw.js                 # Service worker
├── e2e/
│   └── app.spec.ts          # End-to-end tests
├── index.html               # HTML entry point
├── vite.config.ts           # Vite configuration
├── tsconfig.json            # TypeScript configuration
└── playwright.config.ts     # Playwright configuration
```

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
