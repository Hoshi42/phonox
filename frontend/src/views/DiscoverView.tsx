import { useMemo, useState } from 'react'
import type { RegisterRecord } from '../services/registerApi'
import { Icon } from '../ui/Icon'
import { formatEuro, Group, GroupBy, groupRecords } from '../features/collection'
import styles from './DiscoverView.module.css'

interface DiscoverViewProps {
  records: RegisterRecord[]
  onPick: (by: GroupBy, key: string) => void
}

const SEGMENTS: Array<{ id: GroupBy; label: string }> = [
  { id: 'artist', label: 'Artists' },
  { id: 'genre', label: 'Genres' },
  { id: 'decade', label: 'Decades' },
]

export default function DiscoverView({ records, onPick }: DiscoverViewProps) {
  const [by, setBy] = useState<GroupBy>('artist')
  const [alphabetical, setAlphabetical] = useState(false)
  const [filter, setFilter] = useState('')

  const groups = useMemo(() => {
    const all = groupRecords(records, by)
    const text = filter.trim().toLocaleLowerCase()
    const matching = text ? all.filter(group => group.label.toLocaleLowerCase().includes(text)) : all
    if (by === 'decade') return matching.sort((a, b) => Number(a.key) - Number(b.key))
    return alphabetical ? [...matching].sort((a, b) => a.label.localeCompare(b.label)) : matching
  }, [records, by, filter, alphabetical])

  const renderGroup = (group: Group) => (
    <li key={group.key}>
      <button type="button" className={styles.row} onClick={() => onPick(by, group.key)}>
        <span className={`${styles.thumb} ${by === 'artist' ? styles.round : ''}`}>
          {group.cover ? <img src={group.cover} alt="" loading="lazy" decoding="async" /> : <Icon name="disc" />}
        </span>
        <span className={styles.label}>
          <strong>{group.label}</strong>
          <span>{group.count} {group.count === 1 ? 'record' : 'records'} · {formatEuro(group.value)}</span>
        </span>
        <Icon name="chevron-right" size={18} />
      </button>
    </li>
  )

  return (
    <div className={styles.view}>
      <div className={styles.scroll}>
        <header className={styles.header}>
          <h1>Discover</h1>
          <p>Browse your collection by artist, genre or decade.</p>
        </header>

        <div className={styles.sticky}>
          <div className={styles.segmented} role="tablist" aria-label="Browse by">
            {SEGMENTS.map(segment => (
              <button
                key={segment.id}
                type="button"
                role="tab"
                aria-selected={by === segment.id}
                className={by === segment.id ? styles.active : ''}
                onClick={() => { setBy(segment.id); setFilter('') }}
              >
                {segment.label}
              </button>
            ))}
          </div>
          <div className={styles.tools}>
            <label className={styles.filter}>
              <Icon name="search" size={16} />
              <span className="visually-hidden">Filter list</span>
              <input
                type="search"
                placeholder={`Filter ${by === 'decade' ? 'decades' : `${by}s`}…`}
                value={filter}
                onChange={event => setFilter(event.target.value)}
              />
            </label>
            {by !== 'decade' && (
              <button
                type="button"
                className={styles.sortToggle}
                aria-pressed={alphabetical}
                onClick={() => setAlphabetical(value => !value)}
              >
                {alphabetical ? 'A–Z' : 'Most'}
              </button>
            )}
          </div>
        </div>

        {groups.length === 0 ? (
          <p className={styles.none}>{records.length ? 'Nothing matches your filter.' : 'Add records to browse them here.'}</p>
        ) : (
          <ul className={styles.list}>{groups.map(renderGroup)}</ul>
        )}
      </div>
    </div>
  )
}
