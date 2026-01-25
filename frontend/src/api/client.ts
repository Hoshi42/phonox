/**
 * API client for communicating with Phonox FastAPI backend.
 */

export interface ApiError {
  detail: string
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
      console.log('[API] Using VITE_API_URL from environment:', this.baseUrl)
    } else if (typeof window !== 'undefined' && window.location.hostname) {
      this.baseUrl = `http://${window.location.hostname}:8000`
      console.log('[API] Using hostname detection fallback:', this.baseUrl)
    } else {
      this.baseUrl = 'http://localhost:8000'
      console.log('[API] Using localhost fallback:', this.baseUrl)
    }
    
    console.log('[API] ApiClient initialized with baseUrl:', this.baseUrl)
    console.log('[API] window.location.hostname:', typeof window !== 'undefined' ? window.location.hostname : 'N/A')
    console.log('[API] import.meta.env.VITE_API_URL:', import.meta.env.VITE_API_URL || 'Not set')
  }

  async identify(files: File[]): Promise<Record<string, unknown>> {
    const formData = new FormData()
    files.forEach((file) => {
      // Use 'files' as the field name to match FastAPI's List[UploadFile] parameter
      formData.append('files', file)
    })

    const url = `${this.baseUrl}/api/v1/identify`
    console.log('[API] identify() - Starting upload...')
    console.log('[API] identify() - Base URL:', this.baseUrl)
    console.log('[API] identify() - Full URL:', url)
    console.log('[API] identify() - Files count:', files.length, files.map(f => ({ name: f.name, size: f.size, type: f.type })))
    console.log('[API] identify() - User Agent:', navigator.userAgent)
    console.log('[API] identify() - Online:', navigator.onLine)

    try {
      console.log('[API] identify() - Sending fetch request...')
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      })

      console.log('[API] identify() - Received response')
      console.log('[API] identify() - Response status:', response.status, response.statusText)
      console.log('[API] identify() - Response headers:', Object.fromEntries(response.headers.entries()))

      if (!response.ok) {
        console.log('[API] identify() - Response not OK, attempting to parse error...')
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

      console.log('[API] identify() - Parsing successful response...')
      const result = await response.json()
      console.log('[API] identify() - Success result:', result)
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
    const url = `${this.baseUrl}/api/v1/identify/${recordId}`
    console.log('[API] getResult() - Fetching from:', url)

    try {
      const response = await fetch(url)

      if (!response.ok) {
        console.error('[API] getResult() - Response not OK:', response.status, response.statusText)
        if (response.status === 404) {
          throw new Error('Record not found')
        }
        throw new Error('Failed to fetch result')
      }

      const result = await response.json()
      console.log('[API] getResult() - Got result:', result)
      return result
    } catch (error) {
      console.error('[API] getResult() - Network error:', error)
      throw error
    }
  }

  async review(recordId: string, corrections: Record<string, unknown>): Promise<Record<string, unknown>> {
    const response = await fetch(`${this.baseUrl}/api/v1/identify/${recordId}/review`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(corrections),
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

    const response = await fetch(`${this.baseUrl}/api/v1/identify/${recordId}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        metadata: stringMetadata,
      }),
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
    const response = await fetch(`${this.baseUrl}/health`)
    return response.json()
  }

  async reanalyze(recordId: string, files: File[]): Promise<{ record_id: string; id?: string }> {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append('files', file)
    })

    const url = `${this.baseUrl}/api/v1/reanalyze/${recordId}`
    console.log('[API] reanalyze() - Re-analyzing record:', recordId)
    console.log('[API] reanalyze() - Files count:', files.length, files.map(f => ({ name: f.name, size: f.size, type: f.type })))

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      })

      console.log('[API] reanalyze() - Response status:', response.status, response.statusText)

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
      console.log('[API] reanalyze() - Success:', result)
      return result
    } catch (error) {
      console.error('[API] reanalyze() - Failed:', error)
      throw error
    }
  }
}

export const apiClient = new ApiClient()
