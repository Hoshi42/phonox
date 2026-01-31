/**
 * VinylRegister Component
 * 
 * Personal vinyl collection register/library view.
 * Features:
 * - View all records in user's collection
 * - Toggle between list and grid display modes
 * - Sort by artist, title, year, or estimated value
 * - Filter by genre
 * - Select record to view/edit details
 * - Delete records from collection
 * - Collection statistics and analytics
 * 
 * @component
 * @param {Object} props - Component props
 * @param {RegisterRecord[]} props.records - User's vinyl collection
 * @param {Function} props.onClose - Callback to close register view
 * @param {Function} props.onDeleteRecord - Callback to delete a record
 * @param {Function} props.onRecordSelect - Callback when record is selected
 * @returns {JSX.Element} Register modal interface
 */

import { useState } from 'react'
import { RegisterRecord } from '../services/registerApi'
import styles from './VinylRegister.module.css'

const API_BASE = import.meta.env.VITE_API_URL
  || (typeof window !== 'undefined' && window.location.hostname
    ? `http://${window.location.hostname}:8000`
    : 'http://localhost:8000')

interface VinylRegisterProps {
  records: RegisterRecord[]
  onClose: () => void
  onDeleteRecord: (recordId: string) => void
  onRecordSelect: (record: RegisterRecord) => void
}

interface CollectionAnalysis {
  summary: string
  loading: boolean
  error: string | null
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
  const [searchText, setSearchText] = useState<string>('')
  const [analysis, setAnalysis] = useState<CollectionAnalysis>({
    summary: '',
    loading: false,
    error: null
  })

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
    // Genre filter
    if (filterGenre) {
      const genres = record.genres || []
      if (!genres.some(genre => 
        genre.toLowerCase().includes(filterGenre.toLowerCase())
      )) {
        return false
      }
    }
    
    // Text search filter - search across artist, title, label, catalog number, barcode
    if (searchText) {
      const searchLower = searchText.toLowerCase()
      const artist = (record.artist || '').toLowerCase()
      const title = (record.title || '').toLowerCase()
      const label = (record.label || '').toLowerCase()
      const catalogNumber = (record.catalog_number || '').toLowerCase()
      const barcode = (record.barcode || '').toLowerCase()
      
      const matches = artist.includes(searchLower) ||
                     title.includes(searchLower) ||
                     label.includes(searchLower) ||
                     catalogNumber.includes(searchLower) ||
                     barcode.includes(searchLower)
      
      if (!matches) return false
    }
    
    return true
  })

  const totalValue = filteredRecords.reduce((sum, record) => sum + getRecordValue(record), 0)

  const allGenres = [...new Set(
    records.flatMap(record => record.genres || [])
  )].sort()

  const handleEstimateCollection = async () => {
    setAnalysis({ summary: '', loading: true, error: null })
    
    try {
      // Compile collection summary data
      const totalRecords = records.length
      const totalValue = records.reduce((sum, record) => sum + getRecordValue(record), 0)
      
      // Genre analysis
      const genreCount: Record<string, number> = {}
      records.forEach(record => {
        (record.genres || []).forEach(genre => {
          genreCount[genre] = (genreCount[genre] || 0) + 1
        })
      })
      
      // Decade distribution
      const decadeCount: Record<string, number> = {}
      records.forEach(record => {
        if (record.year) {
          const decade = Math.floor(record.year / 10) * 10
          const decadeLabel = `${decade}s`
          decadeCount[decadeLabel] = (decadeCount[decadeLabel] || 0) + 1
        }
      })
      
      // Condition analysis
      const conditionCount: Record<string, number> = {}
      records.forEach(record => {
        const condition = record.condition || 'Unknown'
        conditionCount[condition] = (conditionCount[condition] || 0) + 1
      })
      
      // Top artists
      const artistCount: Record<string, number> = {}
      records.forEach(record => {
        const artist = record.artist || 'Unknown'
        artistCount[artist] = (artistCount[artist] || 0) + 1
      })
      const topArtists = Object.entries(artistCount)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 10)
        .map(([artist, count]) => `${artist} (${count})`)
      
      // Build collection summary prompt
      const collectionSummary = `
VINYL COLLECTION ANALYSIS REQUEST

Collection Overview:
- Total Records: ${totalRecords}
- Total Estimated Value: €${totalValue}
- Average Value per Record: €${(totalValue / totalRecords).toFixed(2)}

Genre Distribution:
${Object.entries(genreCount)
  .sort(([,a], [,b]) => b - a)
  .slice(0, 15)
  .map(([genre, count]) => `- ${genre}: ${count} records`)
  .join('\n')}

Decade Distribution:
${Object.entries(decadeCount)
  .sort()
  .reverse()
  .map(([decade, count]) => `- ${decade}: ${count} records`)
  .join('\n')}

Condition Distribution:
${Object.entries(conditionCount)
  .map(([condition, count]) => `- ${condition}: ${count} records`)
  .join('\n')}

Top 10 Artists:
${topArtists.map((artist, i) => `${i + 1}. ${artist}`).join('\n')}

Please analyze this vinyl collection as a professional record appraiser and collector would. Provide insights on:
1. Collection composition and strengths
2. Rarity and value assessment
3. Market potential and investment value
4. Recommendations for growth and improvement
5. Notable gaps or opportunities for completing sets
6. Suggestions for preservation and care
Keep your analysis professional but personable, suitable for a collector.
`

      // Send to Claude for analysis
      const response = await fetch(`${API_BASE}/api/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: collectionSummary
        })
      })

      if (!response.ok) {
        throw new Error('Failed to analyze collection')
      }

      const data = await response.json()
      setAnalysis({
        summary: data.message || '',
        loading: false,
        error: null
      })
    } catch (err) {
      setAnalysis({
        summary: '',
        loading: false,
        error: err instanceof Error ? err.message : 'Failed to analyze collection'
      })
    }
  }

  const handleDownloadReport = () => {
    if (!analysis.summary) return

    // Create markdown report with metadata
    const timestamp = new Date().toLocaleString('de-DE')
    const totalValue = records.reduce((sum, record) => sum + getRecordValue(record), 0)
    
    const report = `# Vinyl Collection Analysis Report

**Generated:** ${timestamp}  
**Total Records:** ${records.length}  
**Estimated Total Value:** €${totalValue.toFixed(2)}  

---

## Professional Analysis

${analysis.summary}

---

*Report generated by Phonox Vinyl Intelligence*
`

    const blob = new Blob([report], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const filename = `phonox-collection-analysis-${new Date().toISOString().slice(0, 10)}.md`
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const renderMarkdown = (text: string) => {
    // Simple markdown rendering - split by common patterns
    const parts: (string | JSX.Element)[] = []
    let lastIndex = 0

    // Pattern for bold text **text**
    const boldRegex = /\*\*([^*]+)\*\*/g
    let match
    const boldMatches = Array.from(text.matchAll(boldRegex))

    if (boldMatches.length === 0) {
      return text
    }

    boldMatches.forEach((m, i) => {
      // Add text before this match
      if (m.index! > lastIndex) {
        parts.push(text.substring(lastIndex, m.index))
      }
      // Add bold text
      parts.push(
        <strong key={`bold-${i}`}>{m[1]}</strong>
      )
      lastIndex = m.index! + m[0].length
    })

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex))
    }

    return parts
  }

  const handleDownloadCsv = () => {
    const csvEscape = (value: unknown) => {
      if (value === null || value === undefined) return ''
      const str = String(value)
      if (/[;"\n]/.test(str)) {
        return `"${str.replace(/"/g, '""')}"`
      }
      return str
    }

    const headers = [
      'Artist',
      'Title',
      'Year',
      'Label',
      'Catalog Number',
      'Barcode',
      'Genres',
      'Estimated Value (EUR)',
      'Condition',
      'User Tag',
      'Confidence (%)',
      'Spotify URL'
    ]

    const rows = records.map((record) => {
      const value = getRecordValue(record)
      const confidence = record.confidence != null ? Math.round(record.confidence * 100) : ''
      // Prepend apostrophe to barcode to force text format in spreadsheets
      const barcodeValue = record.barcode ? `'${record.barcode}` : ''
      // Convert decimal point to comma for European locale
      const estimatedValue = value ? value.toFixed(2).replace('.', ',') : ''
      return [
        `"${csvEscape(record.artist || '')}"`,
        `"${csvEscape(record.title || '')}"`,
        `"${record.year ?? ''}"`,
        `"${csvEscape(record.label || '')}"`,
        `"${csvEscape(record.catalog_number || '')}"`,
        `"${barcodeValue}"`,
        `"${csvEscape((record.genres || []).join(', '))}"`,
        `"${estimatedValue}"`,
        `"${csvEscape(record.condition || '')}"`,
        `"${csvEscape(record.user_tag || '')}"`,
        confidence ? `"${confidence}"` : `""`,
        `"${csvEscape(record.spotify_url || '')}"`
      ]
    })

    const csvContent = [
      headers.map(csvEscape).join(';'),
      ...rows.map((row) => row.join(';'))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
    link.href = url
    link.setAttribute('download', `phonox-register-${timestamp}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

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
              onClick={handleEstimateCollection}
              className={styles.analyzeBtn}
              title="Analyze collection professionally"
              disabled={analysis.loading}
            >
              {analysis.loading ? '⏳ Analyzing...' : '📊 Analyze Collection'}
            </button>
            <button
              onClick={handleDownloadCsv}
              className={styles.csvBtn}
              title="Download CSV"
            >
              ⬇️ CSV
            </button>
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
            <input
              type="text"
              placeholder="🔍 Search artist, title, label..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className={styles.searchInput}
            />
            
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
                          const title = record.title || 'Unknown Title'
                          const artist = record.artist || 'Unknown Artist'
                          const ok = window.confirm(
                            `Remove "${title}" by ${artist} from your register?`
                          )
                          if (ok) {
                            onDeleteRecord(record.id)
                          }
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

        {/* Collection Analysis Modal */}
        {analysis.summary && (
          <div className={styles.analysisOverlay} onClick={() => setAnalysis({ ...analysis, summary: '' })}>
            <div className={styles.analysisModal} onClick={(e) => e.stopPropagation()}>
              <div className={styles.analysisHeader}>
                <h3>📊 Collection Analysis</h3>
                <div className={styles.analysisActions}>
                  <button 
                    onClick={handleDownloadReport}
                    className={styles.downloadBtn}
                    title="Download as Markdown"
                  >
                    ⬇️ Report
                  </button>
                  <button 
                    onClick={() => setAnalysis({ ...analysis, summary: '' })}
                    className={styles.closeBtn}
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div className={styles.analysisContent}>
                {analysis.error ? (
                  <p className={styles.error}>{analysis.error}</p>
                ) : (
                  <div className={styles.analysisText}>
                    {analysis.summary.split('\n').map((paragraph, i) => {
                      // Handle different markdown elements
                      if (paragraph.startsWith('##')) {
                        return (
                          <h3 key={i} className={styles.analysisHeading}>
                            {paragraph.replace(/^#+\s*/, '')}
                          </h3>
                        )
                      }
                      if (paragraph.startsWith('###')) {
                        return (
                          <h4 key={i} className={styles.analysisSubheading}>
                            {paragraph.replace(/^#+\s*/, '')}
                          </h4>
                        )
                      }
                      if (paragraph.startsWith('-') || paragraph.startsWith('•')) {
                        return (
                          <li key={i} className={styles.analysisListItem}>
                            {renderMarkdown(paragraph.replace(/^[-•]\s*/, ''))}
                          </li>
                        )
                      }
                      if (paragraph.startsWith('1.') || /^\d+\./.test(paragraph)) {
                        return (
                          <li key={i} className={styles.analysisListItem}>
                            {renderMarkdown(paragraph.replace(/^\d+\.\s*/, ''))}
                          </li>
                        )
                      }
                      return (
                        paragraph.trim() && (
                          <p key={i} className={styles.analysisParagraph}>
                            {renderMarkdown(paragraph)}
                          </p>
                        )
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}