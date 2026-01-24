/**
 * API client for communicating with Phonox FastAPI backend.
 */

export interface ApiError {
  detail: string
}

export class ApiClient {
  private baseUrl: string

  constructor(baseUrl?: string) {
    // Determine API URL based on environment:
    // The browser ALWAYS needs to use localhost (the Docker service name 'backend' is not resolvable from the browser)
    
    if (baseUrl) {
      this.baseUrl = baseUrl
    } else if (import.meta.env.VITE_API_URL) {
      this.baseUrl = import.meta.env.VITE_API_URL
    } else {
      // Always use localhost:8000 from the browser
      // (Docker service name 'backend' only works inside the Docker network, not from the browser)
      this.baseUrl = 'http://localhost:8000'
    }
    
    console.log('[API] ApiClient initialized with baseUrl:', this.baseUrl)
    console.log('[API] window.location.hostname:', typeof window !== 'undefined' ? window.location.hostname : 'N/A')
  }

  async identify(files: File[]): Promise<{ id: string }> {
    const formData = new FormData()
    files.forEach((file) => {
      // Use 'files' as the field name to match FastAPI's List[UploadFile] parameter
      formData.append('files', file)
    })

    const url = `${this.baseUrl}/api/v1/identify`
    console.log('[API] identify() - Uploading to:', url)
    console.log('[API] identify() - Files:', files.map(f => ({ name: f.name, size: f.size, type: f.type })))

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      })

      console.log('[API] identify() - Response status:', response.status, response.statusText)

      if (!response.ok) {
        try {
          const error = (await response.json()) as ApiError
          console.error('[API] identify() - Error response:', error)
          throw new Error(error.detail || 'Upload failed')
        } catch (e) {
          console.error('[API] identify() - Failed to parse error response:', e)
          throw new Error(`Upload failed: ${response.statusText}`)
        }
      }

      const result = await response.json()
      console.log('[API] identify() - Success:', result)
      // Backend returns record_id, but we need id
      return { id: result.record_id || result.id }
    } catch (error) {
      console.error('[API] identify() - Network error:', error)
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
    const response = await fetch(`${this.baseUrl}/api/v1/identify/${recordId}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        metadata,
      }),
    })

    if (!response.ok) {
      try {
        const error = (await response.json()) as ApiError
        throw new Error(error.detail || 'Chat failed')
      } catch {
        throw new Error(`Chat failed: ${response.statusText}`)
      }
    }

    return response.json()
  }

  async getHealth(): Promise<Record<string, unknown>> {
    const response = await fetch(`${this.baseUrl}/health`)
    return response.json()
  }
}

export const apiClient = new ApiClient()
