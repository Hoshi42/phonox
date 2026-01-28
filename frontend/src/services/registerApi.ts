/**
 * Register API client for vinyl collection management
 */

// Helper to add cache-busting for mobile browsers
function getCacheHeaders(): HeadersInit {
  const isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
  if (isMobile) {
    return {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    }
  }
  return {}
}

// More robust API base URL detection with fallback
const API_BASE = (() => {
  // First try environment variable (highest priority)
  if (import.meta.env.VITE_API_URL) {
    console.log('[RegisterAPI] Using VITE_API_URL:', import.meta.env.VITE_API_URL)
    return import.meta.env.VITE_API_URL
  }
  
  // Fallback to hostname detection
  if (typeof window !== 'undefined' && window.location.hostname) {
    const fallbackUrl = `http://${window.location.hostname}:8000`
    console.log('[RegisterAPI] Using hostname fallback:', fallbackUrl)
    return fallbackUrl
  }
  
  // Final fallback
  console.log('[RegisterAPI] Using localhost fallback')
  return 'http://localhost:8000'
})()

console.log('[RegisterAPI] Final API_BASE:', API_BASE)

export interface RegisterRecord {
  id: string
  artist?: string
  title?: string
  year?: number
  label?: string
  spotify_url?: string
  catalog_number?: string
  barcode?: string  // UPC/EAN barcode
  genres?: string[]
  estimated_value_eur?: number
  condition?: string
  user_notes?: string
  confidence?: number
  created_at: string
  updated_at: string
  image_urls: string[]
  user_tag?: string
}

export interface RegisterRequest {
  record_id: string
  artist?: string | null
  title?: string | null
  year?: number | null
  label?: string | null
  catalog_number?: string | null
  barcode?: string | null
  genres?: string[]
  estimated_value_eur?: number | null
  condition?: string | null
  user_notes?: string | null
  spotify_url?: string | null
  user_tag?: string
}

class RegisterApiClient {
  private baseUrl: string

  constructor() {
    this.baseUrl = `${API_BASE}/api/register`
    console.log('[RegisterAPI] Initialized with API_BASE:', API_BASE)
    console.log('[RegisterAPI] Full baseUrl:', this.baseUrl)
    console.log('[RegisterAPI] VITE_API_URL:', import.meta.env.VITE_API_URL || 'Not set')
    console.log('[RegisterAPI] window.location.hostname:', typeof window !== 'undefined' ? window.location.hostname : 'N/A')
  }

  async getRegister(userTag?: string, fetchOptions?: RequestInit): Promise<RegisterRecord[]> {
    const url = userTag 
      ? `${this.baseUrl}/?user_tag=${encodeURIComponent(userTag)}&_t=${Date.now()}`
      : `${this.baseUrl}/?_t=${Date.now()}`
    
    console.log('[RegisterAPI] getRegister() - Starting request...')
    console.log('[RegisterAPI] getRegister() - URL:', url)
    console.log('[RegisterAPI] getRegister() - userTag:', userTag)

    try {
      console.log('[RegisterAPI] getRegister() - Sending fetch request...')
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...getCacheHeaders(),
          ...fetchOptions?.headers
        },
        ...fetchOptions
      })

      console.log('[RegisterAPI] getRegister() - Response received')
      console.log('[RegisterAPI] getRegister() - Status:', response.status, response.statusText)

      if (!response.ok) {
        let errorText = ''
        try {
          errorText = await response.text()
          console.error('[RegisterAPI] getRegister() - Error response body:', errorText)
        } catch (e) {
          console.error('[RegisterAPI] getRegister() - Could not read error response:', e)
        }
        throw new Error(`Failed to get register: ${response.status} ${response.statusText} - ${errorText}`)
      }

      const data = await response.json()
      console.log('[RegisterAPI] getRegister() - Success:', data.length, 'records received')
      return data
    } catch (error) {
      console.error('[RegisterAPI] getRegister() - Caught error:', error)
      console.error('[RegisterAPI] getRegister() - Error type:', error instanceof Error ? error.constructor.name : typeof error)
      console.error('[RegisterAPI] getRegister() - Error message:', error instanceof Error ? error.message : String(error))
      if (error instanceof Error && error.stack) {
        console.error('[RegisterAPI] getRegister() - Error stack:', error.stack)
      }
      throw error
    }
  }

  async addToRegister(request: RegisterRequest): Promise<RegisterRecord> {
    const response = await fetch(`${this.baseUrl}/add`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`Failed to add to register: ${response.statusText}`)
    }

    return response.json()
  }

  async updateRegisterRecord(request: RegisterRequest): Promise<RegisterRecord> {
    const response = await fetch(`${this.baseUrl}/update`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`Failed to update register record: ${response.statusText}`)
    }

    return response.json()
  }

  async removeFromRegister(recordId: string, userTag?: string): Promise<void> {
    const url = userTag 
      ? `${this.baseUrl}/${recordId}?user_tag=${encodeURIComponent(userTag)}`
      : `${this.baseUrl}/${recordId}`
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to remove from register: ${response.statusText}`)
    }
  }

  async uploadImages(recordId: string, files: File[]): Promise<{uploaded_images: Array<{id: string, filename: string, url: string}>}> {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })

    const response = await fetch(`${this.baseUrl}/images/${recordId}`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      throw new Error(`Failed to upload images: ${response.statusText}`)
    }

    return response.json()
  }

  async deleteImages(recordId: string, imageUrls: string[]): Promise<void> {
    const response = await fetch(`${this.baseUrl}/images/${recordId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ image_urls: imageUrls }),
    })

    if (!response.ok) {
      throw new Error(`Failed to delete images: ${response.statusText}`)
    }
  }

  getImageUrl(imageId: string): string {
    return `${this.baseUrl}/images/${imageId}`
  }
}

export const registerApiClient = new RegisterApiClient()