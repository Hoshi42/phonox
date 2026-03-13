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
import { RegisterRecord, registerApiClient } from '../services/registerApi'
import VinylSpinner from './VinylSpinner'
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
  onAnalysisReport?: (reportContent: string) => void
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
  onRecordSelect,
  onAnalysisReport
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
  
  // Track moved records to update UI immediately
  const [movedRecordIds, setMovedRecordIds] = useState<Set<string>>(new Set())
  
  // Move record state
  const [moveDialog, setMoveDialog] = useState({
    show: false,
    recordId: '',
    recordTitle: '',
    recordArtist: '',
    availableUsers: [] as string[],
    selectedUser: '',
    newUserName: '',
    isCreatingUser: false,
    loading: false,
    error: ''
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

  // Filter out moved records and apply other filters
  const filteredRecords = sortedRecords.filter(record => {
    // Skip moved records
    if (movedRecordIds.has(record.id)) {
      return false
    }
    
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
      // Compile complete collection data as JSON
      const totalRecords = records.length
      const totalValue = records.reduce((sum, record) => sum + getRecordValue(record), 0)
      
      const collectionData = {
        metadata: {
          total_records: totalRecords,
          total_value_eur: Math.round(totalValue),
          average_value_eur: parseFloat((totalValue / totalRecords).toFixed(2)),
          analysis_date: new Date().toISOString()
        },
        records: records.map(record => ({
          artist: record.artist || 'Unknown',
          title: record.title || 'Unknown',
          year: record.year || null,
          label: record.label || 'Unknown',
          genres: record.genres || [],
          condition: record.condition || 'Unknown',
          value_eur: getRecordValue(record)
        }))
      }

      const collectionSummary = `
Analyze this complete vinyl collection and provide professional insights:

${JSON.stringify(collectionData, null, 2)}

Please analyze this vinyl collection as a professional record appraiser and collector would. Provide detailed insights on:

1. **Collection Composition & Strengths**
   - Genre distribution and specialization areas
   - Decade coverage and historical breadth
   - Label diversity and notable publishers
   - Overall character and focus of the collection

2. **Rarity & Value Assessment**
   - Estimated total collection value accuracy
   - Identification of particularly valuable or rare records
   - Condition impact on market value
   - Hidden gems or underappreciated records

3. **Market Potential & Investment Value**
   - Current market demand for this collection's focus areas
   - Appreciation potential for key genres/labels
   - Liquidity assessment (ease of selling)
   - Price trend analysis for collection genres

4. **Recommendations for Growth & Improvement**
   - Gaps in major artist discographies
   - Genre areas that would strengthen the collection
   - Recommended next acquisitions based on collection focus
   - Complementary albums or artists to pursue

5. **Notable Patterns, Gaps & Opportunities**
   - Underrepresented decades or genres
   - Opportunities for completing collections/series
   - Artist catalog gaps
   - Special edition or variant opportunities

6. **Preservation & Care Suggestions**
   - Storage recommendations based on condition distribution
   - Maintenance tips for collection longevity
   - Value protection strategies
   - Climate and environmental considerations

Keep your analysis professional yet personable, suitable for a serious collector.

IMPORTANT: Do NOT recommend switching to other services or platforms like Discogs. Focus on optimizing their current Phonox management system.
`

      // Send to Claude for analysis
      const response = await fetch(`${API_BASE}/api/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: collectionSummary,
          collection_analysis: true
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

  const handleMoveRecord = async (record: RegisterRecord) => {
    try {
      setMoveDialog(prev => ({ ...prev, loading: true, error: '' }))
      
      // Fetch available users
      const users = await registerApiClient.getUsers()
      
      // Filter out the current user
      const otherUsers = users.filter(u => u !== record.user_tag)
      
      setMoveDialog({
        show: true,
        recordId: record.id,
        recordTitle: record.title || 'Unknown Title',
        recordArtist: record.artist || 'Unknown Artist',
        availableUsers: otherUsers,
        selectedUser: otherUsers.length > 0 ? otherUsers[0] : '',
        newUserName: '',
        isCreatingUser: otherUsers.length === 0,
        loading: false,
        error: ''
      })
    } catch (err) {
      setMoveDialog(prev => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : 'Failed to load users'
      }))
    }
  }

  const handleMoveRecordConfirm = async () => {
    if (!moveDialog.selectedUser && !moveDialog.newUserName) {
      setMoveDialog(prev => ({ ...prev, error: 'Please select or enter a user' }))
      return
    }

    const targetUser = moveDialog.newUserName || moveDialog.selectedUser

    try {
      setMoveDialog(prev => ({ ...prev, loading: true, error: '' }))
      
      // Move the record
      await registerApiClient.moveRecord(
        moveDialog.recordId,
        targetUser,
        records.find(r => r.id === moveDialog.recordId)?.user_tag
      )

      // Add to moved records set to update UI immediately
      setMovedRecordIds(prev => new Set([...prev, moveDialog.recordId]))

      // Close the move dialog
      setMoveDialog(prev => ({ ...prev, show: false }))
      
      // Check if any records remain after this move
      const remainingRecords = records.filter(r => !movedRecordIds.has(r.id) && r.id !== moveDialog.recordId)
      
      if (remainingRecords.length === 0) {
        // No records left for current user - close register to let parent handle user selection
        setTimeout(() => onClose(), 800)
      }
    } catch (err) {
      setMoveDialog(prev => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : 'Failed to move record'
      }))
    }
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

  const parseAnalysisContent = (text: string) => {
    const lines = text.split('\n')
    const elements: JSX.Element[] = []
    let i = 0

    while (i < lines.length) {
      const line = lines[i]

      // Skip separator lines
      if (line.trim().match(/^-{3,}$|^_{3,}$/)) {
        i++
        continue
      }

      // Headers
      if (line.startsWith('##')) {
        elements.push(
          <h3 key={i} className={styles.analysisHeading}>
            {line.replace(/^#+\s*/, '')}
          </h3>
        )
        i++
        continue
      }

      if (line.startsWith('###')) {
        elements.push(
          <h4 key={i} className={styles.analysisSubheading}>
            {line.replace(/^#+\s*/, '')}
          </h4>
        )
        i++
        continue
      }

      // Table detection and rendering
      if (line.includes('|')) {
        const tableLines = []
        let isHeader = false
        while (i < lines.length && lines[i].includes('|')) {
          tableLines.push(lines[i])
          i++
        }

        if (tableLines.length > 0) {
          elements.push(
            <div key={`table-${i}`} className={styles.tableWrapper}>
              <table className={styles.analysisTable}>
                <tbody>
                  {tableLines.map((tableLine, idx) => {
                    // Skip separator rows
                    if (tableLine.trim().match(/^\|[\s\-:]+\|/)) {
                      isHeader = true
                      return null
                    }

                    const cells = tableLine
                      .split('|')
                      .filter(cell => cell.trim())
                      .map(cell => cell.trim())

                    if (isHeader && idx === 0) {
                      return (
                        <thead key={`header-${idx}`}>
                          <tr>
                            {cells.map((cell, cidx) => (
                              <th key={cidx}>{cell}</th>
                            ))}
                          </tr>
                        </thead>
                      )
                    }

                    return (
                      <tr key={`row-${idx}`}>
                        {cells.map((cell, cidx) => (
                          <td key={cidx}>{cell}</td>
                        ))}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )
        }
        continue
      }

      // Bullet points
      if (line.trim().match(/^[-•]\s/)) {
        elements.push(
          <li key={i} className={styles.analysisListItem}>
            {renderMarkdown(line.replace(/^[-•]\s*/, ''))}
          </li>
        )
        i++
        continue
      }

      // Numbered lists
      if (line.trim().match(/^\d+\.\s/)) {
        elements.push(
          <li key={i} className={styles.analysisListItem}>
            {renderMarkdown(line.replace(/^\d+\.\s*/, ''))}
          </li>
        )
        i++
        continue
      }

      // Regular paragraphs
      if (line.trim()) {
        elements.push(
          <p key={i} className={styles.analysisParagraph}>
            {renderMarkdown(line)}
          </p>
        )
      }

      i++
    }

    return elements
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
              {filteredRecords.length} records • Total value: €{totalValue.toFixed(2)}
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
                          handleMoveRecord(record)
                        }}
                        className={styles.moveBtn}
                        title="Move to another user"
                      >
                        👤
                      </button>
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
        {(analysis.summary || analysis.loading) && (
          <div className={styles.analysisOverlay} onClick={() => !analysis.loading && setAnalysis({ ...analysis, summary: '' })}>
            <div className={styles.analysisModal} onClick={(e) => e.stopPropagation()}>
              <div className={styles.analysisHeader}>
                <h3>📊 Collection Analysis</h3>
                <div className={styles.analysisActions}>
                  {analysis.summary && (
                    <>
                      <button 
                        onClick={() => {
                          if (onAnalysisReport) {
                            onAnalysisReport(analysis.summary)
                          }
                        }}
                        className={styles.chatBtn}
                        title="Discuss in Chat"
                      >
                        💬 Chat
                      </button>
                      <button 
                        onClick={handleDownloadReport}
                        className={styles.downloadBtn}
                        title="Download as Markdown"
                      >
                        ⬇️ Report
                      </button>
                    </>
                  )}
                  <button 
                    onClick={() => !analysis.loading && setAnalysis({ ...analysis, summary: '' })}
                    className={styles.closeBtn}
                    disabled={analysis.loading}
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div className={styles.analysisContent}>
                {analysis.loading ? (
                  <VinylSpinner 
                    message="Analyzing your collection..."
                    subtext="Professional valuation in progress"
                  />
                ) : analysis.error ? (
                  <p className={styles.error}>{analysis.error}</p>
                ) : (
                  <div className={styles.analysisText}>
                    {parseAnalysisContent(analysis.summary)}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Move Record Modal */}
        {moveDialog.show && (
          <div className={styles.moveOverlay} onClick={() => setMoveDialog(prev => ({ ...prev, show: false }))}>
            <div className={styles.moveModal} onClick={(e) => e.stopPropagation()}>
              <div className={styles.moveHeader}>
                <h3>👤 Move Record to Another User</h3>
                <button 
                  onClick={() => setMoveDialog(prev => ({ ...prev, show: false }))}
                  className={styles.closeModalBtn}
                >
                  ✕
                </button>
              </div>
              
              <div className={styles.moveContent}>
                <p className={styles.moveRecordInfo}>
                  Moving: <strong>{moveDialog.recordTitle}</strong> by <strong>{moveDialog.recordArtist}</strong>
                </p>

                {moveDialog.error && (
                  <p className={styles.moveError}>{moveDialog.error}</p>
                )}

                {moveDialog.isCreatingUser ? (
                  <div className={styles.moveFormGroup}>
                    <label htmlFor="newUserName">Create New User</label>
                    <input
                      id="newUserName"
                      type="text"
                      placeholder="Enter new user name"
                      value={moveDialog.newUserName}
                      onChange={(e) => setMoveDialog(prev => ({ ...prev, newUserName: e.target.value }))}
                      className={styles.moveInput}
                    />
                  </div>
                ) : (
                  <>
                    <div className={styles.moveFormGroup}>
                      <label htmlFor="selectedUser">Select User</label>
                      <select
                        id="selectedUser"
                        value={moveDialog.selectedUser}
                        onChange={(e) => setMoveDialog(prev => ({ ...prev, selectedUser: e.target.value }))}
                        className={styles.moveSelect}
                      >
                        {moveDialog.availableUsers.map(user => (
                          <option key={user} value={user}>
                            {user}
                          </option>
                        ))}
                      </select>
                    </div>

                    <button
                      onClick={() => setMoveDialog(prev => ({ ...prev, isCreatingUser: true, newUserName: '', selectedUser: '' }))}
                      className={styles.createUserLink}
                    >
                      + Create a new user
                    </button>
                  </>
                )}
              </div>

              <div className={styles.moveActions}>
                <button
                  onClick={() => {
                    if (moveDialog.isCreatingUser) {
                      setMoveDialog(prev => ({ ...prev, isCreatingUser: false, newUserName: '' }))
                    } else {
                      setMoveDialog(prev => ({ ...prev, show: false }))
                    }
                  }}
                  className={styles.moveCancel}
                  disabled={moveDialog.loading}
                >
                  {moveDialog.isCreatingUser ? 'Back' : 'Cancel'}
                </button>
                <button
                  onClick={handleMoveRecordConfirm}
                  className={styles.moveConfirm}
                  disabled={moveDialog.loading || (!moveDialog.selectedUser && !moveDialog.newUserName)}
                >
                  {moveDialog.loading ? '⏳ Moving...' : '✓ Move Record'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}