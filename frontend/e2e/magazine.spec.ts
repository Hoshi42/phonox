import { test, expect, Page } from '@playwright/test'
import type { MagazineSettings, MagazineStatus } from '../src/services/magazineApi'

const defaultMagazineSettings: MagazineSettings = {
  title: 'My Vinyl Collection', subtitle: '', display_name: '', preface: '',
  cover_image_id: null, include_notes: false, research: true, refresh_values: true, consent: false,
}

function magazine(user: string, overrides: Partial<MagazineStatus> = {}): MagazineStatus {
  return {
    id: null, user_tag: user, status: 'not_created', phase: '', progress: null, error: null,
    edition: 0, page_count: 0, record_count: 0, published_at: null, has_pdf: false,
    draft_version: 0, changes: { added: 0, changed: 0, removed: 0 },
    draft: null, settings: { ...defaultMagazineSettings, title: `${user}'s magazine` },
    research_step_limit: 20, estimated_cost_eur: 0.48, warnings: [], ...overrides,
  }
}

async function openCollection(page: Page) {
  await page.goto('/')
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name: 'Profile' }).click()
  await page.getByRole('button', { name: /PDF Magazine/ }).click()
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('phonox_username', 'alice'))
  await page.route('**/api/register/**', async route => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/register/users') {
      await route.fulfill({ json: ['alice', 'bob'] })
    } else {
      const user = url.searchParams.get('user_tag') || 'alice'
      await route.fulfill({ json: [{
        id: `${user}-record`, user_tag: user, artist: `${user} Artist`, title: `${user} Album`,
        year: 1984, estimated_value_eur: 12.5, genres: ['Jazz'], image_urls: [],
        created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
      }] })
    }
  })
})

test('existing magazine opens without generation and user switch resets its context', async ({ page }) => {
  let starts = 0
  await page.route('**/api/magazine**', async route => {
    const user = new URL(route.request().url()).searchParams.get('user_tag') || 'alice'
    if (route.request().method() === 'POST') starts++
    await route.fulfill({ json: magazine(user, user === 'alice' ? {
      id: 'alice-magazine', status: 'complete', has_pdf: true, edition: 1,
      record_count: 1, page_count: 8, published_at: '2026-11-08T12:00:00',
    } : {}) })
  })
  await openCollection(page)
  await expect(page.getByRole('link', { name: 'Open magazine' })).toHaveAttribute('href', /user_tag=alice/)
  await expect(page.getByRole('link', { name: 'Download PDF' })).toHaveAttribute('href', /download=true/)
  expect(starts).toBe(0)
  await page.getByRole('button', { name: 'Switch or add profile' }).click()
  await page.getByRole('button', { name: 'bob' }).click()
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name: 'Profile' }).click()
  await page.getByRole('button', { name: /PDF Magazine/ }).click()
  await expect(page.getByLabel('Magazine title')).toHaveValue("bob's magazine")
  await expect(page.getByRole('link', { name: 'Open magazine' })).toHaveCount(0)
  await expect(page.getByText('One magazine for bob', { exact: false })).toBeVisible()
})

test('research consent, editing, regrouping and publication are wired end to end', async ({ page }) => {
  let current = magazine('alice')
  let prepared = false
  let published = false
  await page.route('**/api/magazine**', async route => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path.endsWith('/prepare')) {
      const settings = request.postDataJSON()
      expect(settings.consent).toBe(true)
      expect(settings.research).toBe(true)
      prepared = true
      current = magazine('alice', { id: 'magazine', status: 'preparing', phase: 'Preparing snapshot' })
      await route.fulfill({ status: 202, json: current })
      current = magazine('alice', {
        id: 'magazine', status: 'draft', draft_version: 1,
        draft: {
          settings: { ...settings, preface: 'A factual foreword.' },
          snapshot_at: '2026-11-08T12:00:00Z', warnings: [], steps_used: 4,
          artists: [{ name: 'alice Artist', portrait: 'A sourced portrait.', sources: [] }],
          records: [{
            id: 'alice-record', artist: 'alice Artist', group: 'alice Artist', title: 'alice Album',
            year: 1984, description: 'A sourced description.', value_eur: 12.5,
            value_kind: 'stored', valued_at: null, valuation_note: 'Date unknown.', sources: [], images: [],
          }],
        },
      })
    } else if (path.endsWith('/draft')) {
      const body = request.postDataJSON()
      expect(body.records[0].group).toBe('Renamed chapter')
      expect(body.preface).toBe('My edited foreword.')
      if (!current.draft) throw new Error('No mock draft exists')
      current.draft.records[0].group = body.records[0].group
      current.draft.settings.preface = body.preface
      current.draft.artists[0].name = 'Renamed chapter'
      current.draft_version++
      await route.fulfill({ json: current })
    } else if (path.endsWith('/publish')) {
      expect(request.postDataJSON().version).toBe(2)
      published = true
      await route.fulfill({ status: 202, json: { ...current, status: 'rendering', phase: 'Typesetting' } })
      current = magazine('alice', { id: 'magazine', status: 'complete', has_pdf: true,
        edition: 1, record_count: 1, page_count: 8 })
    } else {
      await route.fulfill({ json: current })
    }
  })
  await openCollection(page)
  await expect(page.getByRole('button', { name: 'Prepare magazine', exact: true })).toBeDisabled()
  await page.getByLabel('I approve external research', { exact: false }).check()
  await page.getByRole('button', { name: 'Prepare magazine', exact: true }).click()
  await expect(page.getByRole('heading', { name: /Editorial preview/ })).toBeVisible()
  await page.getByLabel('Foreword', { exact: true }).fill('My edited foreword.')
  await page.getByText('alice Album · 1984', { exact: true }).click()
  await page.getByLabel('Artist chapter', { exact: false }).fill('Renamed chapter')
  await expect(page.getByLabel('Artist chapter', { exact: false })).toHaveValue('Renamed chapter')
  await expect(page.getByRole('button', { name: 'Approve & create PDF' })).toBeDisabled()
  await page.getByRole('button', { name: 'Save editorial changes' }).click()
  await expect(page.getByText('Renamed chapter · Artist portrait', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Approve & create PDF' }).click()
  await expect(page.getByRole('link', { name: 'Open magazine' })).toBeVisible()
  expect(prepared).toBe(true)
  expect(published).toBe(true)
})

test('update errors are visible and do not remove the existing PDF', async ({ page }) => {
  await page.route('**/api/magazine**', async route => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 500, json: { detail: 'Research provider unavailable' } })
    } else {
      await route.fulfill({ json: magazine('alice', {
        id: 'magazine', status: 'complete', has_pdf: true, edition: 1, record_count: 1,
        changes: { added: 2, changed: 0, removed: 0 },
      }) })
    }
  })
  await openCollection(page)
  await expect(page.getByText(/Since the last edition: 2 new/)).toBeVisible()
  await page.getByLabel('I approve external research', { exact: false }).check()
  await page.getByRole('button', { name: 'Update magazine / prepare draft' }).click()
  await expect(page.getByRole('alert')).toContainText('Research provider unavailable')
  await expect(page.getByRole('link', { name: 'Open magazine' })).toBeVisible()
})

test('a running job shows measurable progress and elapsed time, also while collapsed', async ({ page }) => {
  let progress: MagazineStatus['progress'] = {
    label: 'Freezing collection data and images', done: 120, total: 366, percent: 12.5, elapsed_seconds: 75,
  }
  await page.route('**/api/magazine**', route => route.fulfill({ json: magazine('alice', {
    id: 'm', status: 'preparing', phase: 'Freezing collection data and images', progress,
  }) }))
  await openCollection(page)
  const bar = page.getByRole('progressbar')
  await expect(bar).toHaveAttribute('aria-valuenow', '12.5')
  await expect(page.getByText('120 of 366')).toBeVisible()
  await expect(page.getByText(/1:15/)).toBeVisible()
  await expect(page.getByText('Freezing collection data and images').first()).toBeVisible()

  // The bar is still there when the panel is collapsed.
  await page.getByRole('button', { name: /PDF Magazine/ }).click()
  await expect(page.getByRole('progressbar')).toHaveCount(1)
  await page.getByRole('button', { name: /PDF Magazine/ }).click()

  // Nothing measurable yet: indeterminate, no fake percentage.
  progress = { label: 'Waiting to start', done: 0, total: 0, percent: null, elapsed_seconds: 2 }
  await expect(page.getByRole('progressbar')).not.toHaveAttribute('aria-valuenow', /.+/, { timeout: 8000 })
  await expect(page.getByText('Waiting to start').first()).toBeVisible()
})
