import type { Page } from '@playwright/test'

export interface SampleRecord {
  id: string
  user_tag: string
  artist: string
  title: string
  year: number
  label: string
  genres: string[]
  estimated_value_eur: number
  image_urls: string[]
  created_at: string
  updated_at: string
}

const ARTISTS = ['Miles Davis', 'Kraftklub', 'Beastie Boys', 'Tame Impala', 'Laufey', 'John Coltrane']
const GENRES = [['Jazz'], ['Rock', 'Indie'], ['Hip Hop'], ['electronic'], ['Electronic', 'Pop'], ['Jazz', 'Modal']]

/** Deterministic records spread over several artists, genres and decades. */
export function sampleRecords(user: string, count = 18): SampleRecord[] {
  return Array.from({ length: count }, (_, index) => {
    const artist = ARTISTS[index % ARTISTS.length]
    return {
      id: `${user}-record-${index}`,
      user_tag: user,
      artist,
      title: `${artist} Album ${index + 1}`,
      year: 1960 + (index % 6) * 10 + (index % 5),
      label: 'Test Label',
      genres: GENRES[index % GENRES.length],
      estimated_value_eur: 10 + index,
      image_urls: [`/api/register/images/${user}-image-${index}`],
      created_at: `2026-01-${String((index % 27) + 1).padStart(2, '0')}T10:00:00Z`,
      updated_at: '2026-01-01T00:00:00Z',
    }
  })
}

const COVER = (seed: string) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300"><rect width="300" height="300" fill="hsl(${
    [...seed].reduce((sum, char) => sum + char.charCodeAt(0), 0) % 360
  } 55% 45%)"/><circle cx="150" cy="150" r="90" fill="#111"/><circle cx="150" cy="150" r="20" fill="#eee"/></svg>`

interface SeedOptions {
  user?: string
  users?: string[]
  records?: SampleRecord[]
  /** Records per user when `records` is not given. */
  count?: number
  /** Analysis returned by GET /api/analysis; null (default) means none stored. */
  analysis?: { summary: string; record_count: number; total_value_eur: number | null; created_at: string } | null
}

/**
 * Selects a profile and mocks the register and analysis endpoints so tests never depend on real data.
 * Must be called before page.goto(). Returns the analyses the app tried to save.
 */
export async function seedApp(page: Page, options: SeedOptions = {}): Promise<{ analysisSaves: unknown[] }> {
  const user = options.user ?? 'alice'
  const users = options.users ?? [user, 'bob']
  const analysisSaves: unknown[] = []
  let analysis = options.analysis ?? null
  await page.addInitScript(
    (name: string) => { if (name) localStorage.setItem('phonox_username', name) },
    user,
  )
  await page.route('**/api/analysis**', async route => {
    if (route.request().method() === 'PUT') {
      const saved = route.request().postDataJSON()
      analysisSaves.push(saved)
      analysis = { ...saved, created_at: '2026-11-09T10:00:00' }
      await route.fulfill({ json: { user_tag: user, ...analysis } })
    } else if (analysis) {
      await route.fulfill({ json: { user_tag: user, ...analysis } })
    } else {
      await route.fulfill({ status: 404, json: { detail: 'No analysis has been saved for this user.' } })
    }
  })
  await page.route('**/api/register/**', async route => {
    const url = new URL(route.request().url())
    if (route.request().method() !== 'GET') {
      await route.fulfill({ json: {} })
    } else if (url.pathname === '/api/register/users') {
      await route.fulfill({ json: users })
    } else if (url.pathname.startsWith('/api/register/images/')) {
      await route.fulfill({ contentType: 'image/svg+xml', body: COVER(url.pathname) })
    } else {
      const owner = url.searchParams.get('user_tag') || user
      await route.fulfill({ json: options.records ?? sampleRecords(owner, options.count) })
    }
  })
  return { analysisSaves }
}

export const MAGAZINE_DEFAULTS = {
  title: 'My Vinyl Collection', subtitle: '', display_name: '', preface: '',
  cover_image_id: null, include_notes: false, research: true, refresh_values: true, consent: false,
}
