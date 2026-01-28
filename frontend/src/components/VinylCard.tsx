/**
 * VinylCard Component
 * 
 * Displays identified vinyl record metadata with editing capabilities.
 * Features:
 * - View/edit record metadata (artist, title, year, label, etc.)
 * - Image management (upload, view, delete)
 * - Value estimation with market lookup
 * - Add to personal register
 * - Web search results from identification
 * - Confidence score visualization
 * 
 * @component
 * @param {VinylCardProps} props - Component props
 * @returns {JSX.Element} Vinyl record card interface
 */

import { useState, useMemo, useEffect } from 'react'
import { VinylRecord } from '../App'
import styles from './VinylCard.module.css'
import { registerApiClient } from '../services/registerApi'
import VinylSpinner from './VinylSpinner'

const API_BASE = import.meta.env.VITE_API_URL
  || (typeof window !== 'undefined' && window.location.hostname
    ? `http://${window.location.hostname}:8000`
    : 'http://localhost:8000')

interface VinylCardProps {
  record: VinylRecord | null
  uploadedImages?: File[]
  onMetadataUpdate?: (metadata: any) => void
  onImageAdd?: (files: FileList) => void
  onImageRemove?: (index: number) => void
  onAddToRegister?: (record: VinylRecord) => void
  onUpdateRegister?: (record: VinylRecord) => void
  onRegisterSuccess?: () => void
  onReanalyze?: (images: File[]) => void
  onAddChatMessage?: (content: string, role?: 'user' | 'assistant' | 'system') => void
  isInRegister?: boolean
  currentUser?: string
  isCheckingValue?: boolean
  onSetIsCheckingValue?: (value: boolean) => void
}

export default function VinylCard({ 
  record, 
  uploadedImages = [], 
  onMetadataUpdate,
  onImageAdd,
  onImageRemove,
  onAddToRegister,
  onUpdateRegister,
  onRegisterSuccess,
  onReanalyze,
  onAddChatMessage,
  isInRegister = false,
  currentUser,
  isCheckingValue = false,
  onSetIsCheckingValue
}: VinylCardProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editData, setEditData] = useState({
    artist: '',
    title: '',
    year: '',
    label: '',
    spotify_url: '',
    catalog_number: '',
    barcode: '',
    genres: '',
    condition: 'Good',
    estimated_value_eur: '' // ADD estimated_value_eur
  })
  const [deletedImageUrls, setDeletedImageUrls] = useState<Set<string>>(new Set())
  const [showRawData, setShowRawData] = useState(false)
  const [webValue, setWebValue] = useState<string | null>(null)
  const [appliedWebValue, setAppliedWebValue] = useState<number | null>(null)
  const [searchIntermediateResults, setSearchIntermediateResults] = useState<any>(null)
  const [lastRecordIdWithResults, setLastRecordIdWithResults] = useState<string | null>(null)

  // Auto-display intermediate results from image analysis
  useEffect(() => {
    if (!record) {
      console.log('VinylCard: No record')
      return
    }
    
    console.log('VinylCard: useEffect triggered - record_id:', record.record_id)
    console.log('VinylCard: Has intermediate_results?', !!record.intermediate_results)
    console.log('VinylCard: Last record with results:', lastRecordIdWithResults)
    
    // If this is a new record (different record_id), clear old results
    if (record.record_id !== lastRecordIdWithResults) {
      console.log('VinylCard: New record detected, clearing old intermediate results')
      setSearchIntermediateResults(null)
    }
    
    // If we have intermediate results and haven't shown them yet for this record
    if (record.intermediate_results && record.record_id !== lastRecordIdWithResults) {
      console.log('VinylCard: Setting intermediate results from image analysis:', record.intermediate_results)
      setSearchIntermediateResults(record.intermediate_results)
      setLastRecordIdWithResults(record.record_id)
      
      // Send to chat panel
      if (onAddChatMessage) {
        const artist = record.artist || record.metadata?.artist || record.intermediate_results?.artist || '?'
        const title = record.title || record.metadata?.title || record.intermediate_results?.title || '?'
        const analysisMessage = `🔍 **Web Search Analysis: "${artist} - ${title}"**

**Search Query:** ${record.intermediate_results.search_query}

**Sources Found:** ${record.intermediate_results.search_results_count}

**Top Sources:**
${record.intermediate_results.search_sources?.map((s: any, i: number) => `${i+1}. **${s.title}**\n   ${s.content}...`).join('\n\n') || 'No sources'}

---

**Market Analysis:**
${record.intermediate_results.claude_analysis || 'No analysis available'}`
        
        onAddChatMessage(analysisMessage, 'assistant')
      }
    } else if (record.intermediate_results && record.record_id === lastRecordIdWithResults) {
      console.log('VinylCard: Already showed results for this record')
    } else {
      console.log('VinylCard: No intermediate_results in record')
    }
  }, [record?.record_id, record?.intermediate_results, lastRecordIdWithResults])

  // Determine condition from image analysis (simulated)
  const getCondition = () => {
    if (!record) return null
    
    // Check if we have ANY images (uploaded OR database)
    const hasUploadedImages = uploadedImages.length > 0
    const hasDatabaseImages = record.metadata?.image_urls && record.metadata.image_urls.length > 0
    
    if (!hasUploadedImages && !hasDatabaseImages) return null
    
    // In real implementation, this would analyze image quality
    // For now, simulate based on confidence and some randomness
    const conditions = ['Mint (M)', 'Near Mint (NM)', 'Very Good+ (VG+)', 'Very Good (VG)', 'Good+ (G+)', 'Good (G)']
    const index = Math.floor((1 - record.confidence) * conditions.length)
    return conditions[Math.min(index, conditions.length - 1)]
  }

  const getConditionMultiplier = () => {
    const condition = getCondition()
    if (!condition) return 1
    
    if (condition.includes('Mint')) return 1.5
    if (condition.includes('Near Mint')) return 1.3
    if (condition.includes('Very Good+')) return 1.1
    if (condition.includes('Very Good')) return 1.0
    if (condition.includes('Good+')) return 0.8
    return 0.6
  }

  // Calculate estimated value based on record data (memoized to ensure consistency)
  const estimatedValue = useMemo(() => {
    if (!record) return 5 // Default minimum value
    
    // Prefer EUR value from metadata (register or chat updates)
    if (record.metadata?.estimated_value_eur) {
      return record.metadata.estimated_value_eur
    }
    
    // Fallback to USD if available (convert to EUR approximately: USD * 0.92)
    if (record.metadata?.estimated_value_usd) {
      const eurValue = record.metadata.estimated_value_usd * 0.92
      return eurValue
    }
    
    // Basic value estimation logic (this would be enhanced with real data)
    const baseValue = 15 // Starting base value
    const rarityMultiplier = record.metadata?.year && record.metadata.year < 1980 ? 2 : 1
    const labelMultiplier = record.metadata?.label?.toLowerCase().includes('blue note') ? 3 : 1
    const conditionMultiplier = getConditionMultiplier()
    
    const calculatedValue = Math.round(baseValue * rarityMultiplier * labelMultiplier * conditionMultiplier)
    return Math.min(Math.max(calculatedValue, 5), 500) // Cap between €5-€500
  }, [record, isInRegister, uploadedImages.length]) // Recalculate when record or images change

  // Helper function for backwards compatibility
  const getEstimatedValue = () => estimatedValue || 5

  const getConditionColor = () => {
    const condition = record?.metadata?.condition || getCondition()
    if (!condition) return '#9ca3af'
    
    if (condition.includes('Mint')) return '#10b981'
    if (condition.includes('Near Mint')) return '#059669'
    if (condition.includes('Very Good+')) return '#84cc16'
    if (condition.includes('Very Good')) return '#eab308'
    if (condition.includes('Good+')) return '#f59e0b'
    return '#ef4444'
  }

  const handleEdit = () => {
    if (record) {
      setEditData({
        artist: record.metadata?.artist || record.artist || '',
        title: record.metadata?.title || record.title || '',
        year: record.metadata?.year?.toString() || record.year?.toString() || '',
        label: record.metadata?.label || record.label || '',
        spotify_url: record.metadata?.spotify_url || '',
        catalog_number: record.metadata?.catalog_number || record.catalog_number || '',
        barcode: record.metadata?.barcode || record.barcode || '',
        estimated_value_eur: record.metadata?.estimated_value_eur ? String(record.metadata.estimated_value_eur) : '',
        genres: Array.isArray(record.metadata?.genres || record.genres) 
          ? (record.metadata?.genres || record.genres)?.join(', ') || ''
          : '',
        condition: record.metadata?.condition || 'Good',
      })
      setIsEditing(true)
    }
  }

  const handleSave = () => {
    if (onMetadataUpdate) {
      const updatedMetadata = {
        // Allow empty strings for fields that can be deleted
        artist: editData.artist || undefined,
        title: editData.title || undefined,
        year: editData.year ? parseInt(editData.year) : null,  // null instead of undefined to allow deletion
        label: editData.label || null,  // Allow deletion
        spotify_url: editData.spotify_url || null,  // Allow deletion
        catalog_number: editData.catalog_number || null,  // Allow deletion (the issue!)
        barcode: editData.barcode || null,  // Allow deletion
        genres: editData.genres ? editData.genres.split(',').map(g => g.trim()).filter(Boolean) : undefined,
        condition: editData.condition || undefined,
        estimated_value_eur: editData.estimated_value_eur ? parseFloat(editData.estimated_value_eur) : null,  // Allow deletion
      }
      onMetadataUpdate(updatedMetadata)
      console.log('VinylCard: Metadata saved locally (will be persisted when adding/updating in register):', updatedMetadata)
    }
    setIsEditing(false)
    setAppliedWebValue(null)
    setWebValue(null)
  }

  const recheckValue = async () => {
    if (!record?.record_id || !record?.artist || !record?.title) return
    
    onSetIsCheckingValue?.(true)
    setWebValue(null)
    
    try {
      console.log('VinylCard: Requesting web-based value estimation for', record.artist, '-', record.title)
      
      const response = await fetch(`${API_BASE}/api/v1/estimate-value/${record.record_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      
      if (!response.ok) {
        throw new Error(`Value estimation failed: ${response.status}`)
      }
      
      const data = await response.json()
      console.log('VinylCard: Value estimation response:', data)
      
      // Store intermediate results for display
      if (data.intermediate_results) {
        setSearchIntermediateResults(data.intermediate_results)
        console.log('VinylCard: Intermediate results:', data.intermediate_results)
        
        // Format message for chat display
        const chatMessage = `🔍 **Web Search Analysis: "${record.metadata?.artist || record.artist || '?'} - ${record.metadata?.title || record.title || '?'}"**

**Search Query:** ${data.intermediate_results.search_query}

**Sources Found:** ${data.intermediate_results.search_results_count}

**Top Sources:**
${data.intermediate_results.search_sources?.map((s: any, i: number) => `${i+1}. **${s.title}**\n   ${s.content}...`).join('\n\n')}

---

**Market Analysis:**
${data.intermediate_results.claude_analysis}

---
**Estimated Value:** €${data.estimated_value_eur}
**Price Range:** €${data.price_range_min} - €${data.price_range_max}
**Market Condition:** ${data.market_condition}`
        
        // Send to chat panel
        if (onAddChatMessage) {
          onAddChatMessage(chatMessage, 'assistant')
        }
      }
      
      if (data.estimated_value_eur) {
        const value = data.estimated_value_eur
        const range = data.price_range_min && data.price_range_max 
          ? ` (€${data.price_range_min}-€${data.price_range_max})`
          : ''
        const condition = data.market_condition ? ` [${data.market_condition} market]` : ''
        
        setWebValue(`€${value}${range}${condition}`)
        console.log('VinylCard: Web value set to:', value)
      } else {
        setWebValue('No price found')
      }
    } catch (error) {
      console.error('VinylCard: Error checking value:', error)
      setWebValue('Error checking market value')
    } finally {
      onSetIsCheckingValue?.(false)
    }
  }
  
  const applyWebValue = async () => {
    if (!webValue || !record?.record_id || webValue.includes('Error') || webValue === 'No price found') return
    
    try {
      // Extract number from webValue (e.g., "€50" -> "50")
      const priceMatch = webValue.match(/\d+(?:\.\d{2})?/)
      if (!priceMatch) return
      
      const newValue = parseFloat(priceMatch[0])
      
      // Update editData with new value
      setEditData(prev => ({
        ...prev,
        estimated_value_eur: String(newValue)
      }))
      
      // Also update record.metadata immediately so Update in Register will use the new value
      if (onMetadataUpdate) {
        onMetadataUpdate({
          estimated_value_eur: newValue
        })
      }
      
      // Show the applied value in the display immediately
      setAppliedWebValue(newValue)
      
      console.log('VinylCard: Web value applied and saved to metadata:', newValue)
    } catch (error) {
      console.error('Error applying web value:', error)
    }
  }

  const handleRegisterAction = async () => {
    if (!record) return
    
    // Use values from record.metadata (which were saved via handleSave)
    // This ensures we use the latest user-edited values
    const estimatedValue = record.metadata?.estimated_value_eur || getEstimatedValue()
    const condition = record.metadata?.condition || getCondition()
    const year = record.metadata?.year || record.year
    
    // Use edited spotify_url from metadata if available
    const spotifyUrlToSave = record.metadata?.spotify_url || undefined
    
    try {
      if (isInRegister) {
        // Delete images first if any were marked for deletion
        if (deletedImageUrls.size > 0) {
          await registerApiClient.deleteImages(record.record_id, Array.from(deletedImageUrls))
          console.log('VinylCard: Deleted images:', Array.from(deletedImageUrls))
        }
        
        // Upload new images if available
        if (uploadedImages.length > 0) {
          await registerApiClient.uploadImages(record.record_id, uploadedImages)
        }
        
        // Update existing record in register with ALL metadata fields
        // Send actual values (including null/empty) to allow deletion
        await registerApiClient.updateRegisterRecord({
          record_id: record.record_id,
          artist: record.metadata?.artist !== undefined ? record.metadata.artist : record.artist || undefined,
          title: record.metadata?.title !== undefined ? record.metadata.title : record.title || undefined,
          year: record.metadata?.year !== undefined ? record.metadata.year : record.year || undefined,
          label: record.metadata?.label !== undefined ? record.metadata.label : record.label || undefined,
          catalog_number: record.metadata?.catalog_number !== undefined ? record.metadata.catalog_number : record.catalog_number || undefined,
          barcode: record.metadata?.barcode !== undefined ? record.metadata.barcode : record.barcode || undefined,
          genres: record.metadata?.genres !== undefined ? record.metadata.genres : record.genres || undefined,
          estimated_value_eur: estimatedValue,
          condition: condition,
          user_notes: `Condition: ${condition} - Updated ${new Date().toLocaleDateString()}`,
          spotify_url: spotifyUrlToSave,
          user_tag: currentUser
        })
        onUpdateRegister?.(record)
      } else {
        // Upload images first if available
        if (uploadedImages.length > 0) {
          await registerApiClient.uploadImages(record.record_id, uploadedImages)
        }
        
        // Add to register with ALL metadata fields
        // Send actual values (including null/empty) to allow deletion
        await registerApiClient.addToRegister({
          record_id: record.record_id,
          artist: record.metadata?.artist !== undefined ? record.metadata.artist : record.artist || undefined,
          title: record.metadata?.title !== undefined ? record.metadata.title : record.title || undefined,
          year: record.metadata?.year !== undefined ? record.metadata.year : record.year || undefined,
          label: record.metadata?.label !== undefined ? record.metadata.label : record.label || undefined,
          catalog_number: record.metadata?.catalog_number !== undefined ? record.metadata.catalog_number : record.catalog_number || undefined,
          barcode: record.metadata?.barcode !== undefined ? record.metadata.barcode : record.barcode || undefined,
          genres: record.metadata?.genres !== undefined ? record.metadata.genres : record.genres || undefined,
          estimated_value_eur: estimatedValue,
          condition: condition,
          user_notes: `Condition: ${condition} - Added ${new Date().toLocaleDateString()}`,
          spotify_url: spotifyUrlToSave,
          user_tag: currentUser
        })
        onAddToRegister?.(record)
      }
      
      // Notify parent component of successful register operation
      onRegisterSuccess?.()
      
      // Clear deleted images tracking after successful update
      setDeletedImageUrls(new Set())
      
      console.log('VinylCard: Record successfully updated in register with values:', {
        estimated_value_eur: estimatedValue,
        condition: condition,
        year: year
      })
      
    } catch (error) {
      console.error('Register operation failed:', error)
      alert('Failed to update register. Please try again.')
    }
  }

  const handleCancel = () => {
    setIsEditing(false)
    setEditData({ artist: '', title: '', year: '', label: '', spotify_url: '', catalog_number: '', barcode: '', genres: '', condition: 'Good', estimated_value_eur: '' })
    setAppliedWebValue(null)
    setWebValue(null)
  }

  if (!record) {
    return (
      <div className={styles.card}>
        <div className={styles.placeholder}>
          <div className={styles.vinylIcon}>🎵</div>
          <h3>No Record Selected</h3>
          <p>Upload images in the chat to analyze a vinyl record</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className={styles.card}>
      {/* Header */}
      <div className={styles.header}>
        <h2>Vinyl Record</h2>
        <div className={styles.actions}>
          {record?.metadata?.spotify_url && (
            <a
              href={record.metadata.spotify_url}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.spotifyHeaderBtn}
              title="Open on Spotify"
            >
              🎧
            </a>
          )}
          {!isEditing ? (
            <button onClick={handleEdit} className={styles.editBtn}>
              ✏️ Edit
            </button>
          ) : (
            <div className={styles.editActions}>
              <button onClick={handleSave} className={styles.saveBtn}>
                ✓ Save
              </button>
              <button onClick={handleCancel} className={styles.cancelBtn}>
                ✕ Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Status */}
      <div className={styles.status}>
        <span className={`${styles.statusBadge} ${styles[record.status]}`}>
          {record.status.toUpperCase()}
        </span>
        <div className={styles.confidence}>
          <span>Confidence: {Math.round(record.confidence * 100)}%</span>
          <div className={styles.confidenceBar}>
            <div 
              className={styles.confidenceFill} 
              style={{ 
                width: `${record.confidence * 100}%`,
                background: record.confidence > 0.8 ? '#10b981' : record.confidence > 0.6 ? '#f59e0b' : '#ef4444'
              }}
            />
          </div>
        </div>
      </div>

      {/* Images */}
      {(uploadedImages.length > 0 || (record.metadata?.image_urls && record.metadata.image_urls.length > 0)) && (
        <div className={styles.images}>
          <h4>Images ({uploadedImages.length + (record.metadata?.image_urls?.length || 0) - deletedImageUrls.size})</h4>
          <div className={styles.imageGrid}>
            {/* Display images from database (loaded from register) */}
            {record.metadata?.image_urls?.map((imageUrl: string, index: number) => (
              !deletedImageUrls.has(imageUrl) && (
                <div key={`db-${index}`} className={styles.imageItem}>
                  <img 
                    src={`${API_BASE}${imageUrl}`} 
                    alt={`Record image ${index + 1}`}
                    className={styles.image}
                  />
                  <button 
                    onClick={() => {
                      const newDeleted = new Set(deletedImageUrls)
                      newDeleted.add(imageUrl)
                      setDeletedImageUrls(newDeleted)
                      console.log('VinylCard: Marked for deletion:', imageUrl)
                    }}
                    className={styles.removeBtn}
                    title="Remove image"
                  >
                    ✕
                  </button>
                </div>
              )
            ))}
            {/* Display uploaded images (preview before saving) */}
            {uploadedImages.map((file, index) => (
              <div key={`upload-${index}`} className={styles.imageItem}>
                <img 
                  src={URL.createObjectURL(file)} 
                  alt={`Uploaded ${index + 1}`}
                  className={styles.image}
                />
                <button 
                  onClick={() => onImageRemove?.(index)}
                  className={styles.removeBtn}
                  title="Remove image"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          <label className={styles.addImageBtn}>
            <input 
              type="file" 
              multiple 
              accept="image/*"
              onChange={(e) => {
                if (e.target.files) {
                  console.log('VinylCard: Adding images:', e.target.files.length)
                  onImageAdd?.(e.target.files)
                  // Reset the input value to allow selecting the same files again (mobile fix)
                  e.target.value = ''
                }
              }}
              style={{ display: 'none' }}
            />
            + Add More Images
          </label>
          {uploadedImages.length > 0 && onReanalyze && (
            <button 
              onClick={() => {
                // Combine existing database images with newly uploaded images for comprehensive re-analysis
                const allImagesToAnalyze = uploadedImages
                console.log('VinylCard: Re-analyzing with', uploadedImages.length, 'new images +', (record.metadata?.image_urls?.length || 0), 'existing images')
                onReanalyze(allImagesToAnalyze)
              }}
              className={styles.reanalyzeBtn}
              title="Re-analyze record with all available images"
            >
              🔄 Re-analyze with {uploadedImages.length + (record.metadata?.image_urls?.length || 0)} total images
            </button>
          )}
        </div>
      )}

      {/* Metadata */}
      <div className={styles.metadata}>
        <h4>Details</h4>
        {!isEditing ? (
          <div className={styles.metadataView}>
            <div className={styles.field}>
              <label>Artist</label>
              <span>{record.metadata?.artist || record.artist || 'Unknown'}</span>
            </div>
            <div className={styles.field}>
              <label>Title</label>
              <span>{record.metadata?.title || record.title || 'Unknown'}</span>
            </div>
            <div className={styles.field}>
              <label>Year</label>
              <span>{record.metadata?.year || record.year || 'Unknown'}</span>
            </div>
            <div className={styles.field}>
              <label>Label</label>
              <span>{record.metadata?.label || record.label || 'Unknown'}</span>
            </div>
            <div className={styles.field}>
              <label>Spotify</label>
              {record.metadata?.spotify_url ? (
                <a href={record.metadata.spotify_url} target="_blank" rel="noreferrer" className={styles.link}>
                  Open in Spotify ↗
                </a>
              ) : (
                <span>Not available</span>
              )}
            </div>
            <div className={styles.field}>
              <label>Catalog #</label>
              <span>{record.metadata?.catalog_number || record.catalog_number || 'Unknown'}</span>
            </div>
            <div className={styles.field}>
              <label>Barcode</label>
              <span>{record.metadata?.barcode || record.barcode || 'Unknown'}</span>
            </div>
            <div className={styles.field}>
              <label>Genres</label>
              <span>
                {Array.isArray(record.metadata?.genres || record.genres) 
                  ? (record.metadata?.genres || record.genres)?.join(', ') || 'Unknown'
                  : 'Unknown'}
              </span>
            </div>
            <div className={styles.field}>
              <label>Condition</label>
              <span style={{ color: getConditionColor() }}>
                {getCondition() || 'Unknown'}
              </span>
            </div>
          </div>
        ) : (
          <div className={styles.metadataEdit}>
            <div className={styles.field}>
              <label>Artist</label>
              <input 
                type="text" 
                value={editData.artist}
                onChange={(e) => setEditData(prev => ({...prev, artist: e.target.value}))}
              />              <label>Estimated Value (EUR):</label>
              <input
                type="number"
                step="0.01"
                value={editData.estimated_value_eur}
                onChange={(e) => setEditData(prev => ({...prev, estimated_value_eur: e.target.value}))}
              />            </div>
            <div className={styles.field}>
              <label>Title</label>
              <input 
                type="text" 
                value={editData.title}
                onChange={(e) => setEditData(prev => ({...prev, title: e.target.value}))}
              />
            </div>
            <div className={styles.field}>
              <label>Year</label>
              <input 
                type="number" 
                value={editData.year}
                onChange={(e) => setEditData(prev => ({...prev, year: e.target.value}))}
              />
            </div>
            <div className={styles.field}>
              <label>Label</label>
              <input 
                type="text" 
                value={editData.label}
                onChange={(e) => setEditData(prev => ({...prev, label: e.target.value}))}
              />
            </div>
            <div className={styles.field}>
              <label>Spotify URL</label>
              <input 
                type="url" 
                value={editData.spotify_url}
                onChange={(e) => setEditData(prev => ({...prev, spotify_url: e.target.value}))}
                placeholder="https://open.spotify.com/album/..."
              />
            </div>
            <div className={styles.field}>
              <label>Catalog #</label>
              <input 
                type="text" 
                value={editData.catalog_number}
                onChange={(e) => setEditData(prev => ({...prev, catalog_number: e.target.value}))}
              />
            </div>
            <div className={styles.field}>
              <label>Barcode (UPC/EAN)</label>
              <input 
                type="text" 
                value={editData.barcode}
                onChange={(e) => setEditData(prev => ({...prev, barcode: e.target.value}))}
                placeholder="123456789012"
              />
            </div>
            <div className={styles.field}>
              <label>Genres</label>
              <input 
                type="text" 
                value={editData.genres}
                onChange={(e) => setEditData(prev => ({...prev, genres: e.target.value}))}
                placeholder="Rock, Jazz, etc."
              />
            </div>
            <div className={styles.field}>
              <label>Condition</label>
              <select 
                value={editData.condition}
                onChange={(e) => setEditData(prev => ({...prev, condition: e.target.value}))}
                className={styles.conditionSelect}
              >
                <option value="Poor">Poor</option>
                <option value="Fair">Fair</option>
                <option value="Good">Good</option>
                <option value="Very Good">Very Good</option>
                <option value="Very Good+">Very Good+</option>
                <option value="Near Mint">Near Mint</option>
                <option value="Mint">Mint</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Value Assessment */}
      {getEstimatedValue() > 0 && (
        <div className={styles.valueSection}>
          <h4>
            💰 Estimated Value
            <button 
              onClick={recheckValue}
              disabled={isCheckingValue || !record?.artist || !record?.title}
              className={styles.recheckBtn}
              title="Search web for current market prices (optional)"
            >
              {isCheckingValue ? '🔄 Searching...' : '🔍 Web Search'}
            </button>
          </h4>
          <div className={styles.valueContent}>
            <div className={styles.valueAmount}>
              €{appliedWebValue !== null ? appliedWebValue : getEstimatedValue()}
              {webValue && !webValue.includes('Error') && webValue !== 'No price found' && (
                <div className={styles.webValue}>
                  <small>Web: {webValue}</small>
                  <button
                    onClick={applyWebValue}
                    className={styles.applyBtn}
                    title="Apply this value to the record"
                  >
                    ✓ Apply
                  </button>
                </div>
              )}
              {webValue && (webValue.includes('Error') || webValue === 'No price found') && (
                <div className={styles.webValue}>
                  <small style={{ color: '#ff6b6b' }}>{webValue}</small>
                </div>
              )}
            </div>
            <div className={styles.valueScale}>
              <div className={styles.scaleBar}>
                {(() => {
                  const value = getEstimatedValue() || 5
                  const position = Math.min(Math.max(((value - 5) / 95 * 100), 0), 100)
                  return (
                    <div 
                      className={styles.scaleIndicator}
                      style={{ 
                        left: `${position}%`
                      }}
                    />
                  )
                })()}
              </div>
              <div className={styles.scaleLabels}>
                <span style={{ left: '0%' }}>€5</span>
                <span style={{ left: '21%' }}>€25</span>
                <span style={{ left: '47%' }}>€50</span>
                <span style={{ left: '100%' }}>€100+</span>
              </div>
            </div>
            {(record?.metadata?.condition || getCondition()) && (
              <div className={styles.conditionBadge}>
                <span 
                  className={styles.conditionLabel}
                  style={{ color: getConditionColor() }}
                >
                  ● {record?.metadata?.condition || getCondition()}
                </span>
                <small>{record?.metadata?.condition ? 'User-defined' : 'Based on image analysis'}</small>
              </div>
            )}
            <div className={styles.valueDisclaimer}>
              <small>
                ⚠️ Estimated value based on available data. Actual market value may vary significantly.
              </small>
            </div>
          </div>
        </div>
      )}

      {/* Register Action */}
      {record && getEstimatedValue() && (
        <div className={styles.registerSection}>
          <button 
            onClick={handleRegisterAction}
            className={`${styles.registerBtn} ${isInRegister ? styles.updateBtn : styles.addBtn}`}
          >
            {isInRegister ? '📝 Update in Register' : '📚 Add to Register'}
          </button>
        </div>
      )}

      {/* Raw Data Toggle */}
      <div className={styles.rawDataSection}>
        <button 
          onClick={() => setShowRawData(!showRawData)}
          className={styles.rawDataToggle}
        >
          {showRawData ? '▼' : '▶'} Raw Data
        </button>
        {showRawData && (
          <div className={styles.rawData}>
            <pre>{JSON.stringify(record, null, 2)}</pre>
          </div>
        )}
      </div>

      {/* Web Search Loading Overlay */}
      {/* Overlay is now handled at App level for full viewport coverage */}
    </div>
    </>
  )
}