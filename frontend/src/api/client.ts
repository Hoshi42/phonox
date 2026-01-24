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
    // 1. Use provided baseUrl
    // 2. Use VITE_API_URL environment variable (set by Docker)
    // 3. Use Docker backend service name (works inside Docker)
    // 4. Use localhost (works for local dev)
    
    if (baseUrl) {
      this.baseUrl = baseUrl
    } else if (import.meta.env.VITE_API_URL) {
      this.baseUrl = import.meta.env.VITE_API_URL
    } else if (typeof window !== 'undefined') {
      // Inside Docker: use backend service name
      // Outside Docker (localhost): use localhost:8000
      const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      this.baseUrl = isLocalhost ? 'http://localhost:8000' : 'http://backend:8000'
    } else {
      this.baseUrl = 'http://backend:8000'
    }
  }

  async identify(files: File[]): Promise<{ id: string }> {
    const formData = new FormData()
    files.forEach((file) => {
      // Use 'files' as the field name to match FastAPI's List[UploadFile] parameter
      formData.append('files', file)
    })

    const response = await fetch(`${this.baseUrl}/api/v1/identify`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      try {
        const error = (await response.json()) as ApiError
        throw new Error(error.detail || 'Upload failed')
      } catch (e) {
        throw new Error(`Upload failed: ${response.statusText}`)
      }
    }

    const result = await response.json()
    // Backend returns record_id, but we need id
    return { id: result.record_id || result.id }
  }

  async getResult(recordId: string): Promise<Record<string, unknown>> {
    const response = await fetch(`${this.baseUrl}/api/v1/identify/${recordId}`)

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Record not found')
      }
      throw new Error('Failed to fetch result')
    }

    return response.json()
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
