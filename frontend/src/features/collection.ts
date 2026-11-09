import type { RegisterRecord } from '../services/registerApi'
import { API_BASE } from '../config'

export type SortKey = 'artist' | 'title' | 'year' | 'value' | 'added'
export type Layout = 'grid' | 'list'

export interface CollectionQuery {
  search: string
  artist: string | null
  genre: string | null
  decade: number | null
  sort: SortKey
  layout: Layout
}

export const EMPTY_QUERY: CollectionQuery = {
  search: '',
  artist: null,
  genre: null,
  decade: null,
  sort: 'artist',
  layout: 'grid',
}

export const SORT_LABELS: Record<SortKey, string> = {
  artist: 'Artist',
  title: 'Title',
  year: 'Year (newest first)',
  value: 'Value (highest first)',
  added: 'Date added (newest first)',
}

export const UNKNOWN_ARTIST = 'Unknown Artist'

/**
 * Stored value when available; otherwise the long-standing heuristic estimate
 * the register has always used for records without a valuation.
 */
export function recordValue(record: RegisterRecord): number {
  if (record.estimated_value_eur) return record.estimated_value_eur
  const baseValue = 15
  const rarityMultiplier = record.year && record.year < 1980 ? 2 : 1
  const labelMultiplier = record.label?.toLowerCase().includes('blue note') ? 3 : 1
  const estimated = Math.round(baseValue * rarityMultiplier * labelMultiplier)
  return Math.min(Math.max(estimated, 5), 500)
}

export function formatEuro(value: number): string {
  return `€${Math.round(value).toLocaleString('en-US')}`
}

export function coverUrl(record: RegisterRecord): string | null {
  const first = record.image_urls?.[0]
  return first ? `${API_BASE}${first}` : null
}

export function artistKey(record: RegisterRecord): string {
  return (record.artist || UNKNOWN_ARTIST).trim().toLocaleLowerCase()
}

export function decadeOf(record: RegisterRecord): number | null {
  return record.year ? Math.floor(record.year / 10) * 10 : null
}

function searchable(record: RegisterRecord): string {
  return [record.artist, record.title, record.label, record.catalog_number, record.barcode]
    .filter(Boolean)
    .join(' ')
    .toLocaleLowerCase()
}

export function isFiltered(query: CollectionQuery): boolean {
  return Boolean(query.search.trim() || query.artist || query.genre || query.decade)
}

export function applyQuery(records: RegisterRecord[], query: CollectionQuery): RegisterRecord[] {
  const text = query.search.trim().toLocaleLowerCase()
  const filtered = records.filter(record => {
    if (query.artist && artistKey(record) !== query.artist.toLocaleLowerCase()) return false
    if (query.genre && !(record.genres || []).some(genre => genre.toLocaleLowerCase() === query.genre!.toLocaleLowerCase())) return false
    if (query.decade && decadeOf(record) !== query.decade) return false
    return !text || searchable(record).includes(text)
  })
  return filtered.sort((a, b) => {
    switch (query.sort) {
      case 'title':
        return (a.title || '').localeCompare(b.title || '')
      case 'year':
        return (b.year || 0) - (a.year || 0)
      case 'value':
        return recordValue(b) - recordValue(a)
      case 'added':
        return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
      default:
        return (a.artist || '').localeCompare(b.artist || '') || (a.title || '').localeCompare(b.title || '')
    }
  })
}

export interface Group {
  key: string
  label: string
  count: number
  value: number
  cover: string | null
}

export type GroupBy = 'artist' | 'genre' | 'decade'

export function groupRecords(records: RegisterRecord[], by: GroupBy): Group[] {
  const groups = new Map<string, Group>()
  const add = (key: string, label: string, record: RegisterRecord) => {
    const group = groups.get(key) || { key, label, count: 0, value: 0, cover: null }
    group.count += 1
    group.value += recordValue(record)
    group.cover = group.cover || coverUrl(record)
    groups.set(key, group)
  }
  for (const record of records) {
    if (by === 'artist') {
      add(artistKey(record), (record.artist || UNKNOWN_ARTIST).trim(), record)
    } else if (by === 'genre') {
      // Genres are matched case-insensitively so "Electronic" and "electronic" form one group.
      for (const genre of new Set((record.genres || []).map(name => name.trim()).filter(Boolean))) {
        add(genre.toLocaleLowerCase(), genre, record)
      }
    } else {
      const decade = decadeOf(record)
      if (decade) add(String(decade), `${decade}s`, record)
    }
  }
  return [...groups.values()].sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
}
