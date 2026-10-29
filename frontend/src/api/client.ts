/**
 * API client for communicating with Phonox FastAPI backend.
 */

import { fetchWithTimeout, TIMEOUT_PRESETS } from './fetchWithTimeout'

export interface ApiError {
  detail: string
}

// Helper to add cache-busting headers for mobile browsers
function getCacheHeaders(): HeadersInit {
  const isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
  if (isMobile) {
    return {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
      // Add timestamp to force fresh response
      'X-Cache-Bust': Date.now().toString()
    }
  }
  return {}
}

// Helper to add cache-busting query parameter for GET requests
function addCacheBustingParam(url: string): string {
  const isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
  if (isMobile) {
    const separator = url.includes('?') ? '&' : '?'
    return `${url}${separator}t=${Date.now()}`
  }
  return url
}

export class ApiClient {
  private baseUrl: string

  constructor(baseUrl?: string) {
    // Determine API URL based on environment with better mobile cache handling
    // The browser ALWAYS needs to use localhost (the Docker service name 'backend' is not resolvable from the browser)

    if (baseUrl) {
      this.baseUrl = baseUrl
    } else if (import.meta.env.VITE_API_URL) {
      this.baseUrl = import.meta.env.VITE_API_URL
    } else if (typeof window !== 'undefined' && window.location.hostname) {
      this.baseUrl = `http://${window.location.hostname}:8000`
    } else {
      this.baseUrl = 'http://localhost:8000'
    }
    
  }

  async identify(files: File[]): Promise<Record<string, unknown>> {
    const formData = new FormData()
    files.forEach((file) => {
      // Use 'files' as the field name to match FastAPI's List[UploadFile] parameter
      formData.append('files', file)
    })

    const url = `${this.baseUrl}/api/v1/identify`

    try {
      const response = await fetchWithTimeout(url, {
        method: 'POST',
        body: formData,
        headers: getCacheHeaders(),
        timeout: TIMEOUT_PRESETS.VERY_LONG // 120s for file upload + value estimation via web scraping
      })


      if (!response.ok) {
        try {
          const error = (await response.json()) as ApiError
          console.error('[API] identify() - Error response:', error)
          throw new Error(error.detail || `Upload failed: ${response.status}`)
        } catch (e) {
          if (e instanceof Error && e.message.includes('Upload failed:')) {
            throw e
          }
          console.error('[API] identify() - Failed to parse error response:', e)
          throw new Error(`Upload failed: ${response.status} ${response.statusText}`)
        }
      }

      const result = await response.json()
      // Return the complete response, not just record_id and status
      return result
    } catch (error) {
      console.error('[API] identify() - Caught error:', error)
      console.error('[API] identify() - Error type:', error instanceof Error ? error.constructor.name : typeof error)
      console.error('[API] identify() - Error message:', error instanceof Error ? error.message : String(error))
      if (error instanceof Error && error.stack) {
        console.error('[API] identify() - Error stack:', error.stack)
      }
      throw error
    }
  }

  async getResult(recordId: string): Promise<Record<string, unknown>> {
    const url = addCacheBustingParam(`${this.baseUrl}/api/v1/identify/${recordId}`)

    try {
      const response = await fetchWithTimeout(url, {
        headers: getCacheHeaders(),
        timeout: TIMEOUT_PRESETS.NORMAL // 30s for polling
      })

      if (!response.ok) {
        console.error('[API] getResult() - Response not OK:', response.status, response.statusText)
        if (response.status === 404) {
          throw new Error('Record not found')
        }
        throw new Error('Failed to fetch result')
      }

      const result = await response.json()
      return result
    } catch (error) {
      console.error('[API] getResult() - Network error:', error)
      throw error
    }
  }

  async review(recordId: string, corrections: Record<string, unknown>): Promise<Record<string, unknown>> {
    const response = await fetchWithTimeout(`${this.baseUrl}/api/v1/identify/${recordId}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(corrections),
      timeout: TIMEOUT_PRESETS.NORMAL // 30s
    })

    if (!response.ok) {
      const error = (await response.json()) as ApiError
      throw new Error(error.detail || 'Review submission failed')
    }

    return response.json()
  }

  async chat(recordId: string, message: string, metadata?: Record<string, unknown>): Promise<Record<string, unknown>> {
    // Convert metadata values to strings for API compatibility
    const stringMetadata = metadata
      ? Object.entries(metadata).reduce(
          (acc, [key, value]) => {
            acc[key] = String(value)
            return acc
          },
          {} as Record<string, string>
        )
      : undefined

    const response = await fetchWithTimeout(`${this.baseUrl}/api/v1/identify/${recordId}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        metadata: stringMetadata,
      }),
      timeout: TIMEOUT_PRESETS.NORMAL // 30s for chat
    })

    if (!response.ok) {
      try {
        const error = (await response.json()) as ApiError
        console.error('[API] Chat error response:', error)
        throw new Error(error.detail || `Chat failed: ${error.detail}`)
      } catch (e) {
        if (e instanceof Error && e.message.includes('Chat failed')) {
          throw e
        }
        console.error('[API] Chat error (no JSON response):', response.statusText)
        throw new Error(`Chat failed: ${response.statusText}`)
      }
    }

    return response.json()
  }

  async getHealth(): Promise<Record<string, unknown>> {
    const url = addCacheBustingParam(`${this.baseUrl}/health`)
    const response = await fetchWithTimeout(url, {
      headers: getCacheHeaders(),
      timeout: TIMEOUT_PRESETS.SHORT // 10s for health check
    })
    return response.json()
  }

  async reanalyze(recordId: string, files: File[], currentRecord?: any, reanalyzeAll?: boolean): Promise<Record<string, unknown>> {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append('files', file)
    })
    
    // Send current record data so backend doesn't need to query database
    if (currentRecord) {
      formData.append('current_record', JSON.stringify(currentRecord))
    }
    
    // Set reanalyze_all flag for complete re-analysis mode
    if (reanalyzeAll) {
      formData.append('reanalyze_all', 'true')
    }

    const url = `${this.baseUrl}/api/v1/reanalyze/${recordId}`

    try {
      const response = await fetchWithTimeout(url, {
        method: 'POST',
        body: formData,
        timeout: TIMEOUT_PRESETS.VERY_LONG // 2m for re-analysis (long operation)
      })


      if (!response.ok) {
        try {
          const error = (await response.json()) as ApiError
          console.error('[API] Re-analysis error response:', error)
          throw new Error(error.detail || `Re-analysis failed: ${response.status}`)
        } catch (e) {
          if (e instanceof Error && e.message.includes('Re-analysis failed')) {
            throw e
          }
          console.error('[API] Re-analysis error (no JSON response):', response.statusText)
          throw new Error(`Re-analysis failed: ${response.statusText}`)
        }
      }

      const result = await response.json()
      return result
    } catch (error) {
      console.error('[API] reanalyze() - Failed:', error)
      throw error
    }
  }
}

export const apiClient = new ApiClient()
