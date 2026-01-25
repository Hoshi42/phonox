import { useState } from 'react'
import { RegisterRecord } from '../services/registerApi'
import styles from './VinylRegister.module.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface VinylRegisterProps {
  records: RegisterRecord[]
  onClose: () => void
  onDeleteRecord: (recordId: string) => void
  onRecordSelect: (record: RegisterRecord) => void
}

export default function VinylRegister({
  records,
  onClose,
  onDeleteRecord,
  onRecordSelect
}: VinylRegisterProps) {
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('grid')
  const [sortBy, setSortBy] = useState<'artist' | 'title' | 'year' | 'value'>('artist')
  const [filterGenre, setFilterGenre] = useState<string>('')

  const getRecordValue = (record: RegisterRecord) => {
    // Use the stored estimated_value_eur if available, otherwise calculate
    if (record.estimated_value_eur) {
      return record.estimated_value_eur
    }
    
    // Fallback calculation (same logic as in VinylCard but without condition multiplier)
    const baseValue = 15
    const rarityMultiplier = record.year && record.year < 1980 ? 2 : 1
    const labelMultiplier = record.label?.toLowerCase().includes('blue note') ? 3 : 1
    const estimatedValue = Math.round(baseValue * rarityMultiplier * labelMultiplier)
    return Math.min(Math.max(estimatedValue, 5), 500) // Cap between €5-€500
  }

  const sortedRecords = [...records].sort((a, b) => {
    switch (sortBy) {
      case 'artist':
        return (a.artist || '').localeCompare(b.artist || '')
      case 'title':
        return (a.title || '').localeCompare(b.title || '')
      case 'year':
        return (b.year || 0) - (a.year || 0)
      case 'value':
        return getRecordValue(b) - getRecordValue(a)
      default:
        return 0
    }
  })

  const filteredRecords = sortedRecords.filter(record => {
    if (!filterGenre) return true
    const genres = record.genres || []
    return genres.some(genre => 
      genre.toLowerCase().includes(filterGenre.toLowerCase())
    )
  })

  const totalValue = filteredRecords.reduce((sum, record) => sum + getRecordValue(record), 0)

  const allGenres = [...new Set(
    records.flatMap(record => record.genres || [])
  )].sort()

  return (
    <div className={styles.registerOverlay}>
      <div className={styles.registerModal}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <h2>🎵 My Vinyl Register</h2>
            <div className={styles.summary}>
              {filteredRecords.length} records • Total value: €{totalValue}
            </div>
          </div>
          <div className={styles.headerRight}>
            <button 
              onClick={onClose}
              className={styles.closeBtn}
              title="Close register"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Controls */}
        <div className={styles.controls}>
          <div className={styles.viewToggle}>
            <button 
              onClick={() => setViewMode('grid')}
              className={`${styles.toggleBtn} ${viewMode === 'grid' ? styles.active : ''}`}
            >
              ⊞ Grid
            </button>
            <button 
              onClick={() => setViewMode('list')}
              className={`${styles.toggleBtn} ${viewMode === 'list' ? styles.active : ''}`}
            >
              ☰ List
            </button>
          </div>

          <div className={styles.filters}>
            <select 
              value={sortBy} 
              onChange={(e) => setSortBy(e.target.value as any)}
              className={styles.sortSelect}
            >
              <option value="artist">Sort by Artist</option>
              <option value="title">Sort by Title</option>
              <option value="year">Sort by Year</option>
              <option value="value">Sort by Value</option>
            </select>

            <select 
              value={filterGenre} 
              onChange={(e) => setFilterGenre(e.target.value)}
              className={styles.genreSelect}
            >
              <option value="">All Genres</option>
              {allGenres.map(genre => (
                <option key={genre} value={genre}>{genre}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Records */}
        <div className={styles.recordsContainer}>
          {filteredRecords.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>📀</div>
              <h3>No records found</h3>
              <p>Your register is empty or no records match your filter.</p>
            </div>
          ) : (
            <div className={`${styles.recordsGrid} ${styles[viewMode]}`}>
              {filteredRecords.map((record) => (
                <div 
                  key={record.id} 
                  className={styles.recordCard}
                  onClick={() => onRecordSelect(record)}
                >
                  {record.image_urls && record.image_urls.length > 0 ? (
                    <div className={styles.recordThumbnail}>
                      <img 
                        src={`${API_BASE}${record.image_urls[0]}`} 
                        alt={`${record.title || 'Record'} cover`}
                        className={styles.thumbnailImage}
                      />
                    </div>
                  ) : (
                    <div className={styles.recordThumbnail}>
                      <div className={styles.noImage}>
                        <span>🎵</span>
                      </div>
                    </div>
                  )}
                  <div className={styles.recordHeader}>
                    <div className={styles.recordInfo}>
                      <h3 className={styles.recordTitle}>
                        {record.title || 'Unknown Title'}
                      </h3>
                      <p className={styles.recordArtist}>
                        {record.artist || 'Unknown Artist'}
                      </p>
                    </div>
                    <div className={styles.recordActions}>
                      {record.spotify_url && (
                        <a
                          href={record.spotify_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={styles.spotifyBtn}
                          title="Open on Spotify"
                          onClick={(e) => e.stopPropagation()}
                        >
                          🎧
                        </a>
                      )}
                      <button 
                        onClick={(e) => {
                          e.stopPropagation()
                          onDeleteRecord(record.id)
                        }}
                        className={styles.deleteBtn}
                        title="Remove from register"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>

                  <div className={styles.recordDetails}>
                    <div className={styles.recordMeta}>
                      <span className={styles.year}>
                        {record.year || 'Unknown'}
                      </span>
                      <span className={styles.label}>
                        {record.label || 'Unknown Label'}
                      </span>
                    </div>
                    
                    {record.genres && record.genres.length > 0 && (
                      <div className={styles.genres}>
                        {record.genres.slice(0, 2).map(genre => (
                          <span key={genre} className={styles.genreTag}>{genre}</span>
                        ))}
                      </div>
                    )}

                    <div className={styles.recordValue}>
                      <span className={styles.valueAmount}>€{getRecordValue(record)}</span>
                      <span className={styles.confidence}>
                        {record.confidence ? Math.round(record.confidence * 100) : 'Unknown'}% confidence
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}