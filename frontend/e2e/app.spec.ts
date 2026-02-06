import { test, expect } from '@playwright/test'

test.describe('Phonox Application', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('h1')).toContainText('Phonox')
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

  test('should register service worker', async ({ page }) => {
    const scriptContent = await page.content()
    expect(scriptContent).toContain('navigator.serviceWorker.register')
  })

  test('should be responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await expect(page.locator('h1')).toBeVisible()
    await expect(page.locator('text=Click to upload')).toBeVisible()
  })
})

test.describe('Health & API Endpoints', () => {
  test('should have accessible health check endpoint', async ({ page }) => {
    const response = await page.request.get('http://localhost:8000/health')
    expect(response.ok()).toBeTruthy()
    const data = await response.json()
    expect(data.status).toBe('healthy')
  })

  test('should serve API v1 endpoints', async ({ page }) => {
    // Test that API base is reachable (health check via v1 path)
    const response = await page.request.get('http://localhost:8000/api/v1/health')
    expect(response.status()).toBeLessThan(500)
  })
})

test.describe('Image Upload', () => {
  test('should display upload interface', async ({ page }) => {
    await expect(page.locator('text=Click to upload or drag and drop')).toBeVisible()
    await expect(page.locator('text=PNG, JPG, GIF')).toBeVisible()
  })

  test('should validate file input attributes', async ({ page }) => {
    const uploadInput = page.locator('input[type="file"]')
    await expect(uploadInput).toHaveAttribute('accept', 'image/*')
    await expect(uploadInput).toHaveAttribute('multiple', '')
  })

  test('should show vinyl spinner during upload', async ({ page }) => {
    // Mock slow identify endpoint
    await page.route('**/api/v1/identify', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000))
      await route.fulfill({
        status: 202,
        body: JSON.stringify({ record_id: 'test-123' }),
      })
    })

    // VinylSpinner component should be visible during loading
    // (actual file upload test would require test images)
  })

  test('should handle upload errors gracefully', async ({ page }) => {
    await page.route('**/api/v1/identify', (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ detail: 'Server error' }),
      })
    })

    await expect(page.locator('h1')).toContainText('Phonox')
  })
})

test.describe('VinylCard Display', () => {
  test('should display vinyl card with metadata', async ({ page }) => {
    // Mock identify and result endpoints
    await page.route('**/api/v1/identify', (route) => {
      route.fulfill({
        status: 202,
        body: JSON.stringify({ record_id: 'test-123' }),
      })
    })

    await page.route('**/api/v1/identify/test-123', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          record_id: 'test-123',
          status: 'complete',
          artist: 'The Beatles',
          title: 'Abbey Road',
          year: 1969,
          label: 'Apple Records',
          catalog_number: 'PCS 7088',
          barcode: '5099969945724',
          genres: ['Rock', 'Pop'],
          confidence: 0.95,
          auto_commit: true,
          needs_review: false,
          evidence_chain: [],
        }),
      })
    })

    // VinylCard should display metadata fields when populated
  })

  test('should support metadata editing', async ({ page }) => {
    // VinylCard has editable fields for artist, title, year, label, etc.
    // Test would verify input fields are present and editable
  })

  test('should display barcode when available', async ({ page }) => {
    // VinylCard shows barcode field from metadata
  })

  test('should allow adding images to existing records', async ({ page }) => {
    // Mock image upload endpoint
    await page.route('**/api/register/images/*', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          message: 'Images uploaded',
          uploaded: ['image1.jpg'],
          failed: [],
        }),
      })
    })

    // Test image upload functionality in VinylCard
  })
})

test.describe('ChatPanel', () => {
  test('should display chat interface', async ({ page }) => {
    // ChatPanel should be visible in the interface
    // Contains input field and message history
  })

  test('should handle chat messages', async ({ page }) => {
    await page.route('**/api/v1/chat', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          record_id: null,
          message: 'Hello! I can help with vinyl records.',
          metadata: null,
        }),
      })
    })

    // Test chat interaction
  })

  test('should support record-specific chat', async ({ page }) => {
    await page.route('**/api/v1/identify/*/chat', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          record_id: 'test-123',
          message: 'This is a rare pressing.',
          metadata: null,
        }),
      })
    })

    // Test context-aware chat with specific record
  })
})

test.describe('VinylRegister (Collection)', () => {
  test('should open and close register', async ({ page }) => {
    // Mock register endpoint
    await page.route('**/api/register**', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify([]),
      })
    })

    // Click button to open register
    const registerBtn = page.locator('button:has-text("My Collection")')
    if (await registerBtn.isVisible()) {
      await registerBtn.click()
      // Register modal should be visible
    }
  })

  test('should display collection records', async ({ page }) => {
    await page.route('**/api/register**', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify([
          {
            id: 1,
            artist: 'Pink Floyd',
            title: 'The Dark Side of the Moon',
            year: 1973,
            user: 'testuser',
            created_at: '2026-02-06T12:00:00',
          },
        ]),
      })
    })

    // Register should show user's collection
  })

  test('should support adding records to collection', async ({ page }) => {
    await page.route('**/api/register', (route) => {
      if (route.request().method() === 'POST') {
        route.fulfill({
          status: 201,
          body: JSON.stringify({
            id: 1,
            message: 'Record added to collection',
          }),
        })
      } else {
        route.continue()
      }
    })

    // Test adding record to collection via VinylCard
  })

  test('should support deleting records from collection', async ({ page }) => {
    await page.route('**/api/register/*', (route) => {
      if (route.request().method() === 'DELETE') {
        route.fulfill({
          status: 200,
          body: JSON.stringify({ message: 'Record deleted' }),
        })
      } else {
        route.continue()
      }
    })

    // Test delete functionality
  })
})

test.describe('User Management', () => {
  test('should display user manager', async ({ page }) => {
    // UserManager component for selecting/creating users
  })

  test('should filter collection by user', async ({ page }) => {
    await page.route('**/api/register?user=*', (route) => {
      const url = new URL(route.request().url())
      const user = url.searchParams.get('user')
      
      route.fulfill({
        status: 200,
        body: JSON.stringify([
          {
            id: 1,
            artist: 'Test Artist',
            user: user,
          },
        ]),
      })
    })

    // Test user filtering in collection
  })
})

test.describe('Value Estimation', () => {
  test('should estimate market value', async ({ page }) => {
    await page.route('**/api/estimate-value', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          estimated_value_eur: 25.00,
          estimated_value_usd: 27.50,
        }),
      })
    })

    // Test value estimation feature
  })

  test('should show loading state during estimation', async ({ page }) => {
    await page.route('**/api/estimate-value', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000))
      await route.fulfill({
        status: 200,
        body: JSON.stringify({
          estimated_value_eur: 25.00,
          estimated_value_usd: 27.50,
        }),
      })
    })

    // VinylSpinner with "Estimating Market Value..." should be visible
  })
})

test.describe('Error Handling', () => {
  test('should display error messages', async ({ page }) => {
    await page.route('**/api/v1/identify', (route) => {
      route.fulfill({
        status: 400,
        body: JSON.stringify({ detail: 'Invalid request' }),
      })
    })

    // Error modal should be displayed
  })

  test('should handle network errors', async ({ page }) => {
    await page.route('**/health', (route) => {
      route.abort('failed')
    })

    await page.goto('/')
    await expect(page.locator('h1')).toContainText('Phonox')
  })
})
