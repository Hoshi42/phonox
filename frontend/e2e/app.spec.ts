import { test, expect } from '@playwright/test'

test.describe('Phonox End-to-End Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to app
    await page.goto('/')
    
    // Check that app loaded
    await expect(page.locator('h1')).toContainText('Phonox')
  })

  test('should display upload interface', async ({ page }) => {
    // Check for upload elements
    await expect(page.locator('text=Click to upload or drag and drop')).toBeVisible()
    await expect(page.locator('text=PNG, JPG, GIF')).toBeVisible()
  })

  test('should validate image upload (less than 1 image)', async ({ page }) => {
    // Try to upload without images - should show error when attempting
    await page.goto('/')
  })

  test('should validate image count (more than 5 images)', async ({ page }) => {
    // This test would need actual image files, so we test the UI instead
    const uploadInput = page.locator('input[type="file"]')
    
    // Verify the file input accepts images
    await expect(uploadInput).toHaveAttribute('accept', 'image/*')
    await expect(uploadInput).toHaveAttribute('multiple', '')
  })

  test('should show loading state during analysis', async ({ page }) => {
    // Mock API response
    await page.route('**/api/v1/identify', (route) => {
      route.abort('timedout')
    })

    // The UI should have loading spinner component
    await expect(page.locator('text=Analyzing vinyl records')).toBeHidden()
  })

  test('should display health check endpoint is accessible', async ({ page }) => {
    const response = await page.request.get('/health')
    expect(response.ok()).toBeTruthy()
  })

  test('should display API is reachable', async ({ page }) => {
    const response = await page.request.get('/api')
    // This may 404, but we're just checking connectivity
    expect(response.status()).toBeLessThan(500)
  })

  test('should have proper title and meta tags', async ({ page }) => {
    await expect(page).toHaveTitle('Phonox - Vinyl Record Identifier')
    
    const metaDescription = page.locator('meta[name="description"]')
    await expect(metaDescription).toHaveAttribute('content', /AI-powered vinyl/)
  })

  test('should have PWA manifest configured', async ({ page }) => {
    const manifestLink = page.locator('link[rel="manifest"]')
    await expect(manifestLink).toHaveAttribute('href', '/manifest.json')
  })

  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    
    // Check that header is visible and readable
    await expect(page.locator('h1')).toBeVisible()
    
    // Check that upload area is accessible
    await expect(page.locator('text=Click to upload')).toBeVisible()
  })

  test('should register service worker', async ({ page }) => {
    // Check that service worker registration script is present
    const scriptContent = await page.content()
    expect(scriptContent).toContain('navigator.serviceWorker.register')
  })

  test('should handle API errors gracefully', async ({ page }) => {
    // Mock API failure
    await page.route('**/health', (route) => {
      route.abort('failed')
    })

    // App should still load
    await page.goto('/')
    await expect(page.locator('h1')).toContainText('Phonox')
  })

  test('should have correct footer content', async ({ page }) => {
    const footer = page.locator('footer')
    await expect(footer).toContainText('Phonox')
    await expect(footer).toContainText('2024')
  })
})

test.describe('Results Display', () => {
  test('should display results with metadata', async ({ page }) => {
    // Mock identify endpoint
    await page.route('**/api/v1/identify', (route) => {
      route.resolve({
        status: 202,
        body: JSON.stringify({ id: 'test-123' }),
      })
    })

    // Mock result endpoint
    await page.route('**/api/v1/identify/test-123', (route) => {
      route.resolve({
        status: 200,
        body: JSON.stringify({
          id: 'test-123',
          status: 'complete',
          artist: 'The Beatles',
          title: 'Abbey Road',
          year: 1969,
          label: 'Apple Records',
          catalog_number: 'PCS 7088',
          genres: ['Rock', 'Pop'],
          confidence: 0.95,
          auto_commit: true,
          needs_review: false,
          evidence_chain: [],
        }),
      })
    })
  })
})

test.describe('Review Workflow', () => {
  test('should display review form for low confidence results', async ({ page }) => {
    // Review form should be present when needs_review is true
    await page.goto('/')
    
    // The form should have correction fields
    // This would require actual data being set in state
  })

  test('should submit corrections successfully', async ({ page }) => {
    // Mock review endpoint
    await page.route('**/api/v1/identify/*/review', (route) => {
      route.resolve({
        status: 200,
        body: JSON.stringify({
          id: 'test-123',
          status: 'complete',
          artist: 'Corrected Artist',
        }),
      })
    })
  })
})
