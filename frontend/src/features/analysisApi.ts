import { API_BASE } from '../config'

export interface StoredAnalysis {
  summary: string
  record_count: number
  total_value_eur: number | null
  created_at: string
}

const url = (user: string) => `${API_BASE}/api/analysis?user_tag=${encodeURIComponent(user)}`

/** The user's latest saved analysis, or null if none exists yet. */
export async function fetchStoredAnalysis(user: string, signal?: AbortSignal): Promise<StoredAnalysis | null> {
  const response = await fetch(url(user), { signal, cache: 'no-store' })
  if (response.status === 404) return null
  if (!response.ok) throw new Error(`Could not load the saved analysis (${response.status})`)
  return response.json()
}

export async function saveAnalysis(
  user: string,
  summary: string,
  recordCount: number,
  totalValue: number,
): Promise<StoredAnalysis> {
  const response = await fetch(url(user), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ summary, record_count: recordCount, total_value_eur: totalValue }),
  })
  if (!response.ok) throw new Error(`The analysis could not be saved (${response.status})`)
  return response.json()
}

/** The backend stores timestamps in UTC without a zone suffix. */
export function parseStoredDate(value: string): Date {
  return new Date(value.endsWith('Z') || /[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`)
}
