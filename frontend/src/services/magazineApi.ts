const API_BASE = import.meta.env.VITE_API_URL
  || (typeof window !== 'undefined' ? `http://${window.location.hostname}:8000` : 'http://localhost:8000')

export interface MagazineSettings {
  title: string
  subtitle: string
  display_name: string
  preface: string
  cover_image_id: string | null
  include_notes: boolean
  research: boolean
  refresh_values: boolean
  consent: boolean
}

export interface MagazineSource {
  title: string
  url: string
  accessed_at: string
}

export interface MagazineImage {
  id: string
  filename: string
  width: number
  height: number
}

export interface MagazineRecord {
  id: string
  artist: string | null
  group: string
  title: string | null
  year: number | null
  description: string
  value_eur: number | null
  value_kind: 'stored' | 'researched' | 'unavailable'
  valued_at: string | null
  valuation_note: string
  sources: MagazineSource[]
  images: MagazineImage[]
}

export interface MagazineArtist {
  name: string
  portrait: string
  sources: MagazineSource[]
}

export interface MagazineDraft {
  settings: MagazineSettings
  snapshot_at: string
  records: MagazineRecord[]
  artists: MagazineArtist[]
  warnings: string[]
  steps_used: number
}

export interface MagazineStatus {
  id: string | null
  user_tag: string
  status: string
  phase: string
  error: string | null
  edition: number
  page_count: number
  record_count: number
  published_at: string | null
  has_pdf: boolean
  draft_version: number
  changes: { added: number; changed: number; removed: number }
  draft: MagazineDraft | null
  settings: MagazineSettings
  research_step_limit: number
  estimated_cost_eur: number
  warnings: string[]
}

export const defaultMagazineSettings: MagazineSettings = {
  title: 'My Vinyl Collection',
  subtitle: '',
  display_name: '',
  preface: '',
  cover_image_id: null,
  include_notes: false,
  research: true,
  refresh_values: true,
  consent: false,
}

class MagazineApi {
  private url(user: string, suffix = '') {
    return `${API_BASE}/api/magazine${suffix}?user_tag=${encodeURIComponent(user)}`
  }

  private async request(user: string, suffix = '', options: RequestInit = {}, query = ''): Promise<MagazineStatus> {
    const response = await fetch(this.url(user, suffix) + query, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
      cache: 'no-store',
    })
    if (!response.ok) {
      const text = await response.text()
      let detail = text
      try {
        const body: { detail?: unknown } = JSON.parse(text)
        detail = typeof body.detail === 'string' ? body.detail : text
      } catch {
        console.error('[MagazineAPI] Non-JSON error response:', response.status)
      }
      throw new Error(detail || `Magazine request failed (${response.status})`)
    }
    return response.json()
  }

  status(user: string, includeDraft = true, signal?: AbortSignal) {
    return this.request(user, '', { signal }, `&include_draft=${includeDraft}`)
  }

  prepare(user: string, settings: MagazineSettings) {
    return this.request(user, '/prepare', { method: 'POST', body: JSON.stringify(settings) })
  }

  save(user: string, draft: MagazineDraft, version: number) {
    return this.request(user, '/draft', {
      method: 'PUT',
      body: JSON.stringify({
        version,
        preface: draft.settings.preface,
        records: draft.records.map(record => ({
          id: record.id, group: record.group, description: record.description,
        })),
        artists: draft.artists.map(artist => ({ name: artist.name, portrait: artist.portrait })),
      }),
    })
  }

  publish(user: string, version: number) {
    return this.request(user, '/publish', { method: 'POST', body: JSON.stringify({ version }) })
  }

  cancel(user: string) {
    return this.request(user, '/cancel', { method: 'POST' })
  }

  async remove(user: string) {
    const response = await fetch(this.url(user), { method: 'DELETE' })
    if (!response.ok) throw new Error(`Magazine deletion failed: ${await response.text()}`)
  }

  pdfUrl(user: string, download = false) {
    return this.url(user, '/pdf') + `&download=${download}`
  }

  imageUrl(user: string, id: string) {
    return this.url(user, `/images/${encodeURIComponent(id)}`)
  }
}

export const magazineApi = new MagazineApi()
