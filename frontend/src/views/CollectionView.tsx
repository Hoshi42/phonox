import { useMemo, useState } from 'react'
import type { RegisterRecord } from '../services/registerApi'
import { Icon } from '../ui/Icon'
import { Sheet } from '../ui/Sheet'
import RecordCard from '../ui/RecordCard'
import {
  applyQuery, CollectionQuery, EMPTY_QUERY, formatEuro, groupRecords, isFiltered, Layout,
  recordValue, SORT_LABELS, SortKey,
} from '../features/collection'
import styles from './CollectionView.module.css'

interface CollectionViewProps {
  user: string
  records: RegisterRecord[]
  loading: boolean
  query: CollectionQuery
  onQueryChange: (patch: Partial<CollectionQuery>) => void
  onOpenRecord: (record: RegisterRecord) => void
  onOpenDiscover: () => void
  onOpenProfile: () => void
  onCapture: () => void
}

function Shelf({ title, onMore, children }: { title: string; onMore?: () => void; children: React.ReactNode }) {
  return (
    <section className={styles.shelfSection}>
      <div className={styles.shelfHead}>
        <h2>{title}</h2>
        {onMore && (
          <button type="button" onClick={onMore} className={styles.more}>
            See all <Icon name="chevron-right" size={16} />
          </button>
        )}
      </div>
      <div className={styles.shelf}>{children}</div>
    </section>
  )
}

export default function CollectionView({
  user, records, loading, query, onQueryChange, onOpenRecord, onOpenDiscover, onOpenProfile, onCapture,
}: CollectionViewProps) {
  const [sortOpen, setSortOpen] = useState(false)
  const filtered = isFiltered(query)

  const results = useMemo(() => applyQuery([...records], query), [records, query])
  const totalValue = useMemo(() => records.reduce((sum, record) => sum + recordValue(record), 0), [records])
  const recent = useMemo(
    () => applyQuery([...records], { ...EMPTY_QUERY, sort: 'added' }).slice(0, 10),
    [records],
  )
  const artists = useMemo(() => groupRecords(records, 'artist').slice(0, 14), [records])
  const genres = useMemo(() => groupRecords(records, 'genre').slice(0, 12), [records])
  const resultValue = useMemo(() => results.reduce((sum, record) => sum + recordValue(record), 0), [results])

  const activeChips = [
    query.artist && { label: results[0]?.artist || query.artist, clear: { artist: null } },
    query.genre && { label: query.genre, clear: { genre: null } },
    query.decade && { label: `${query.decade}s`, clear: { decade: null } },
  ].filter(Boolean) as Array<{ label: string; clear: Partial<CollectionQuery> }>

  const grid = query.layout === 'grid'

  return (
    <div className={styles.view}>
      <div className={styles.scroll}>
        <header className={styles.header}>
          <div>
            <h1>Collection</h1>
            <p className={styles.summary}>
              {loading ? 'Loading…' : `${records.length} records · ${formatEuro(totalValue)}`}
            </p>
          </div>
          <button
            type="button"
            className={styles.avatar}
            onClick={onOpenProfile}
            aria-label={`Profile: ${user}`}
          >
            {user.slice(0, 1).toUpperCase()}
          </button>
        </header>

        <div className={styles.toolbar}>
          <label className={styles.search}>
            <Icon name="search" size={18} />
            <span className="visually-hidden">Search collection</span>
            <input
              type="search"
              placeholder="Search artist, title, label…"
              value={query.search}
              onChange={event => onQueryChange({ search: event.target.value })}
              enterKeyHint="search"
            />
          </label>
          <button
            type="button"
            className={styles.iconButton}
            onClick={() => setSortOpen(true)}
            aria-label="Sort and layout"
          >
            <Icon name="sort" size={20} />
          </button>
        </div>

        {activeChips.length > 0 && (
          <div className={styles.chips} role="group" aria-label="Active filters">
            {activeChips.map(chip => (
              <button
                key={chip.label}
                type="button"
                className={styles.chip}
                onClick={() => onQueryChange(chip.clear)}
                aria-label={`Remove filter ${chip.label}`}
              >
                {chip.label} <Icon name="close" size={14} />
              </button>
            ))}
          </div>
        )}

        {loading && !records.length ? (
          <div className={styles.grid} aria-busy="true">
            {Array.from({ length: 6 }, (_, index) => <div key={index} className={styles.skeleton} />)}
          </div>
        ) : !records.length ? (
          <div className={styles.empty}>
            <Icon name="disc" size={44} />
            <h2>Your collection is empty</h2>
            <p>Photograph a record cover and Phonox identifies it for you.</p>
            <button type="button" className={styles.primary} onClick={onCapture}>Capture a record</button>
          </div>
        ) : (
          <>
            {!filtered && (
              <>
                <Shelf title="Recently added">
                  {recent.map(record => (
                    <RecordCard key={record.id} record={record} shelf onOpen={onOpenRecord} />
                  ))}
                </Shelf>
                <Shelf title="Artists" onMore={onOpenDiscover}>
                  {artists.map(group => (
                    <button
                      key={group.key}
                      type="button"
                      className={styles.artist}
                      onClick={() => onQueryChange({ artist: group.key })}
                    >
                      <span className={styles.avatarImage}>
                        {group.cover ? <img src={group.cover} alt="" loading="lazy" /> : <Icon name="user" />}
                      </span>
                      <span className={styles.artistName}>{group.label}</span>
                      <span className={styles.count}>{group.count}</span>
                    </button>
                  ))}
                </Shelf>
                <section className={styles.shelfSection}>
                  <div className={styles.shelfHead}>
                    <h2>Genres</h2>
                    <button type="button" onClick={onOpenDiscover} className={styles.more}>
                      See all <Icon name="chevron-right" size={16} />
                    </button>
                  </div>
                  <div className={styles.chips}>
                    {genres.map(group => (
                      <button
                        key={group.key}
                        type="button"
                        className={styles.chip}
                        onClick={() => onQueryChange({ genre: group.key })}
                      >
                        {group.label} <span className={styles.count}>{group.count}</span>
                      </button>
                    ))}
                  </div>
                </section>
              </>
            )}

            <section className={styles.shelfSection}>
              <div className={styles.shelfHead}>
                <h2>{filtered ? `${results.length} results` : 'All records'}</h2>
                {filtered && <span className={styles.summary}>{formatEuro(resultValue)}</span>}
              </div>
              {results.length === 0 ? (
                <div className={styles.empty}>
                  <h2>No matches</h2>
                  <button type="button" className={styles.primary} onClick={() => onQueryChange({ ...EMPTY_QUERY, sort: query.sort, layout: query.layout })}>
                    Clear filters
                  </button>
                </div>
              ) : (
                <div className={grid ? styles.grid : styles.rows}>
                  {results.map(record => (
                    <RecordCard
                      key={record.id}
                      record={record}
                      layout={query.layout}
                      onOpen={onOpenRecord}
                    />
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </div>

      <Sheet open={sortOpen} title="Sort & layout" onClose={() => setSortOpen(false)}>
        <fieldset className={styles.options}>
          <legend>Sort by</legend>
          {(Object.keys(SORT_LABELS) as SortKey[]).map(key => (
            <label key={key} className={styles.option}>
              <input
                type="radio"
                name="sort"
                checked={query.sort === key}
                onChange={() => onQueryChange({ sort: key })}
              />
              <span>{SORT_LABELS[key]}</span>
            </label>
          ))}
        </fieldset>
        <fieldset className={styles.options}>
          <legend>Layout</legend>
          <div className={styles.segmented}>
            {(['grid', 'list'] as Layout[]).map(layout => (
              <button
                key={layout}
                type="button"
                aria-pressed={query.layout === layout}
                className={query.layout === layout ? styles.segmentActive : ''}
                onClick={() => onQueryChange({ layout })}
              >
                {layout === 'grid' ? 'Grid' : 'List'}
              </button>
            ))}
          </div>
        </fieldset>
      </Sheet>
    </div>
  )
}
