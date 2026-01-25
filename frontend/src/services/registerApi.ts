/**
 * Register API client for vinyl collection management
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface RegisterRecord {
  id: string
  artist?: string
  title?: string
  year?: number
  label?: string
  spotify_url?: string
  catalog_number?: string
  genres?: string[]
  estimated_value_eur?: number
  condition?: string
  user_notes?: string
  confidence?: number
  created_at: string
  updated_at: string
  image_urls: string[]
}

export interface RegisterRequest {
  record_id: string
  estimated_value_eur?: number
  condition?: string
  user_notes?: string
  spotify_url?: string
}

class RegisterApiClient {
  private baseUrl: string

  constructor() {
    this.baseUrl = `${API_BASE}/register`
  }

  async getRegister(): Promise<RegisterRecord[]> {
    const response = await fetch(`${this.baseUrl}/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to get register: ${response.statusText}`)
    }

    return response.json()
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

  async removeFromRegister(recordId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/${recordId}`, {
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

  getImageUrl(imageId: string): string {
    return `${this.baseUrl}/images/${imageId}`
  }
}

export const registerApiClient = new RegisterApiClient()