/**
 * API client for communicating with Phonox FastAPI backend.
 */

export interface ApiError {
  detail: string
}

export class ApiClient {
  private baseUrl: string

  constructor(baseUrl?: string) {
    // Use environment variable if available, otherwise fallback to default
    if (baseUrl) {
      this.baseUrl = baseUrl
    } else if (import.meta.env.VITE_API_URL) {
      this.baseUrl = import.meta.env.VITE_API_URL
    } else {
      this.baseUrl = 'http://localhost:8000'
    }
  }

  async identify(files: File[]): Promise<{ id: string }> {
    const formData = new FormData()
    files.forEach((file, index) => {
      formData.append(`image_${index}`, file)
    })

    const response = await fetch(`${this.baseUrl}/api/v1/identify`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const error = (await response.json()) as ApiError
      throw new Error(error.detail || 'Upload failed')
    }

    return response.json()
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

  async getHealth(): Promise<Record<string, unknown>> {
    const response = await fetch(`${this.baseUrl}/health`)
    return response.json()
  }
}

export const apiClient = new ApiClient()
