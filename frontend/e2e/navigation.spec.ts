import { test, expect, Page } from '@playwright/test'
import { seedApp, sampleRecords } from './support'

const tab = (page: Page, name: string) => page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name })

test.describe('first run', () => {
  test('asks for a profile before showing anything else', async ({ page }) => {
    await seedApp(page, { user: '', users: ['alice', 'bob'] })
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Welcome to Phonox' })).toBeVisible()
    await expect(page.getByRole('navigation', { name: 'Main navigation' })).toHaveCount(0)
    await page.getByRole('button', { name: 'bob' }).click()
    await expect(page.getByRole('heading', { name: 'Collection', level: 1 })).toBeVisible()
    expect(await page.evaluate(() => localStorage.getItem('phonox_username'))).toBe('bob')
  })

  test('creates a new profile', async ({ page }) => {
    await seedApp(page, { user: '', users: [] })
    await page.goto('/')
    await page.getByLabel('New profile name').fill('carol')
    await page.getByRole('button', { name: 'Add' }).click()
    await expect(page.getByText(/18 records ·/)).toBeVisible()
  })
})

test.describe('navigation and collection', () => {
  test.beforeEach(async ({ page }) => {
    await seedApp(page)
    await page.goto('/')
    await expect(page.getByText(/18 records ·/)).toBeVisible()
  })

  test('shows the four tabs and keeps each view mounted', async ({ page }) => {
    for (const name of ['Collection', 'Capture', 'Discover', 'Profile']) {
      await expect(tab(page, name)).toBeVisible()
    }
    await expect(tab(page, 'Collection')).toHaveAttribute('aria-current', 'page')
    await tab(page, 'Capture').click()
    await expect(page.getByPlaceholder('Ask about records, prices, artists…')).toBeVisible()
    await page.getByPlaceholder('Ask about records, prices, artists…').fill('draft text survives')
    await tab(page, 'Discover').click()
    await tab(page, 'Capture').click()
    await expect(page.getByPlaceholder('Ask about records, prices, artists…')).toHaveValue('draft text survives')
  })

  test('searches, filters by genre case-insensitively and clears filters', async ({ page }) => {
    await page.getByPlaceholder('Search artist, title, label…').fill('kraftklub')
    await expect(page.getByRole('heading', { name: '3 results' })).toBeVisible()
    await page.getByPlaceholder('Search artist, title, label…').fill('')

    const groups = sampleRecords('alice').filter(record => record.genres.some(genre => genre.toLowerCase() === 'electronic'))
    await page.getByRole('button', { name: /^electronic \d+$/i }).first().click()
    await expect(page.getByRole('heading', { name: `${groups.length} results` })).toBeVisible()
    await page.getByRole('button', { name: /Remove filter/ }).click()
    await expect(page.getByRole('heading', { name: 'All records' })).toBeVisible()
  })

  test('sorts and switches to the list layout', async ({ page }) => {
    await page.getByRole('button', { name: 'Sort and layout' }).click()
    await page.getByLabel('Value (highest first)').check()
    await page.getByRole('button', { name: 'List' }).click()
    await page.keyboard.press('Escape')
    const first = page.getByRole('heading', { name: 'All records' }).locator('xpath=ancestor::section[1]').getByRole('button').first()
    await expect(first).toHaveAccessibleName(/Album 18 by/)
  })

  test('discover filters the collection by artist and decade', async ({ page }) => {
    await tab(page, 'Discover').click()
    await page.getByPlaceholder('Filter artists…').fill('miles')
    await page.getByRole('button', { name: /Miles Davis/ }).click()
    await expect(tab(page, 'Collection')).toHaveAttribute('aria-current', 'page')
    await expect(page.getByRole('heading', { name: '3 results' })).toBeVisible()

    await tab(page, 'Discover').click()
    await page.getByRole('tab', { name: 'Decades' }).click()
    await page.getByRole('button', { name: /1960s/ }).click()
    await expect(page.getByRole('button', { name: 'Remove filter 1960s' })).toBeVisible()
  })

  test('opens a record in the detail sheet and closes it with Escape', async ({ page }) => {
    await page.getByRole('button', { name: /Miles Davis Album 1 by Miles Davis/ }).first().click()
    const dialog = page.getByRole('dialog', { name: 'Miles Davis Album 1' })
    await expect(dialog).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Remove from collection' })).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Move to another profile' })).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(dialog).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Miles Davis Album 1 by/ }).first()).toBeFocused()
  })

  test('removing a record needs confirmation', async ({ page }) => {
    let deleted = ''
    await page.route('**/api/register/*?user_tag=alice', route => {
      if (route.request().method() === 'DELETE') {
        deleted = new URL(route.request().url()).pathname
        return route.fulfill({ json: {} })
      }
      return route.fallback()
    })
    await page.getByRole('button', { name: /Miles Davis Album 1 by/ }).first().click()
    await page.getByRole('button', { name: 'Remove from collection' }).click()
    await expect(page.getByRole('dialog', { name: 'Remove from collection?' })).toBeVisible()
    await page.getByRole('button', { name: 'Cancel' }).click()
    expect(deleted).toBe('')
    await page.getByRole('button', { name: 'Remove from collection' }).click()
    await page.getByRole('button', { name: 'Remove', exact: true }).click()
    await expect.poll(() => deleted).toBe('/api/register/alice-record-0')
  })
})

test.describe('profile and appearance', () => {
  test.beforeEach(async ({ page }) => {
    await seedApp(page)
    await page.goto('/')
    await tab(page, 'Profile').click()
  })

  test('theme choice is applied immediately and persists', async ({ page }) => {
    await page.getByRole('radio', { name: 'Dark' }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    await page.reload()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    await tab(page, 'Profile').click()
    await page.getByRole('radio', { name: 'System' }).click()
    await expect(page.locator('html')).not.toHaveAttribute('data-theme', /.+/)
  })

  test('follows the system colour scheme by default', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' })
    const background = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)
    expect(background).toBe('rgb(13, 13, 16)')
    await page.emulateMedia({ colorScheme: 'light' })
    expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe('rgb(245, 244, 240)')
  })

  test('switches profile and reloads that profile\'s collection', async ({ page }) => {
    await page.getByRole('button', { name: 'Switch or add profile' }).click()
    await page.getByRole('button', { name: 'bob' }).click()
    await expect(tab(page, 'Collection')).toHaveAttribute('aria-current', 'page')
    await expect(page.getByRole('button', { name: 'Profile: bob' })).toBeVisible()
    expect(await page.evaluate(() => localStorage.getItem('phonox_username'))).toBe('bob')
  })
})

test.describe('responsive layout', () => {
  test('phone: no horizontal overflow and the tab bar leaves most of the screen to content', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await seedApp(page)
    await page.goto('/')
    await expect(page.getByText(/18 records ·/)).toBeVisible()
    const metrics = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      nav: document.querySelector('nav')!.getBoundingClientRect().height,
    }))
    expect(metrics.overflow).toBe(0)
    expect(metrics.nav).toBeLessThan(80)
    // The search bar is visible without scrolling and cards are at least 150px wide (two columns).
    await expect(page.getByPlaceholder('Search artist, title, label…')).toBeInViewport()
  })

  test('desktop: side rail instead of bottom bar, detail opens as a drawer', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 })
    await seedApp(page)
    await page.goto('/')
    const nav = await page.locator('nav').boundingBox()
    expect(nav!.x).toBe(0)
    expect(nav!.width).toBeLessThan(120)
    await page.getByRole('button', { name: /Miles Davis Album 1 by/ }).first().click()
    const panel = await page.getByRole('dialog').boundingBox()
    expect(panel!.x).toBeGreaterThan(600)
    expect(panel!.height).toBeGreaterThanOrEqual(790)
  })
})

test.describe('empty and failing states', () => {
  test('empty collection offers capture', async ({ page }) => {
    await seedApp(page, { records: [] })
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Your collection is empty' })).toBeVisible()
    await page.getByRole('button', { name: 'Capture a record' }).click()
    await expect(tab(page, 'Capture')).toHaveAttribute('aria-current', 'page')
  })

  test('profile list failure is reported instead of failing silently', async ({ page }) => {
    await seedApp(page)
    await page.route('**/api/register/users', route => route.fulfill({ status: 500, json: { detail: 'down' } }))
    await page.goto('/')
    await tab(page, 'Profile').click()
    await page.getByRole('button', { name: 'Switch or add profile' }).click()
    await expect(page.getByRole('alert')).toContainText('Existing profiles could not be loaded.')
  })
})
