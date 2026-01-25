import { useState, useMemo } from 'react'
import { VinylRecord } from '../App'
import styles from './VinylCard.module.css'
import { registerApiClient } from '../services/registerApi'

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
  isInRegister?: boolean
  currentUser?: string
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
  isInRegister = false,
  currentUser
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
  })
  const [showRawData, setShowRawData] = useState(false)
  const [isCheckingValue, setIsCheckingValue] = useState(false)
  const [webValue, setWebValue] = useState<string | null>(null)

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
    const condition = getCondition()
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
        genres: Array.isArray(record.metadata?.genres || record.genres) 
          ? (record.metadata?.genres || record.genres)?.join(', ') || ''
          : '',
      })
      setIsEditing(true)
    }
  }

  const handleSave = () => {
    if (onMetadataUpdate) {
      onMetadataUpdate({
        artist: editData.artist || undefined,
        title: editData.title || undefined,
        year: editData.year ? parseInt(editData.year) : undefined,
        label: editData.label || undefined,
        spotify_url: editData.spotify_url || undefined,
        catalog_number: editData.catalog_number || undefined,
        barcode: editData.barcode || undefined,
        genres: editData.genres ? editData.genres.split(',').map(g => g.trim()).filter(Boolean) : undefined,
      })
    }
    setIsEditing(false)
  }

  const recheckValue = async () => {
    if (!record?.artist || !record?.title || !record?.record_id) return
    
    setIsCheckingValue(true)
    setWebValue(null)
    
    try {
      // Use the record-specific chat endpoint with web search
      const response = await fetch(`/api/v1/identify/${record.record_id}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: `What is the current market value of ${record.artist} - ${record.title}? Please find specific pricing information.`,
        }),
      })

      if (response.ok) {
        const data = await response.json()
        const content = data.message || ''
        
        console.log('Value check response:', { content, sources_used: data.sources_used })
        
        // Extract price information from the response using various patterns
        const pricePatterns = [
          /€(\d+(?:\.\d{2})?)/g, // €XX.XX
          /EUR?\s*(\d+(?:\.\d{2})?)/gi, // EUR XX or €XX
          /\$(\d+(?:\.\d{2})?)/g, // $XX.XX
          /(\d+(?:\.\d{2})?)\s*(?:euros?|€)/gi, // XX euros
          /worth\s*(?:around\s*)?(?:€|EUR)?\s*(\d+(?:\.\d{2})?)/gi, // worth around XX
          /price[d]?\s*(?:around|at|of)?\s*(?:€|EUR)?\s*(\d+(?:\.\d{2})?)/gi, // priced at XX
          /market value\s*(?:around|of|is)?\s*(?:€|EUR)?\s*(\d+(?:\.\d{2})?)/gi, // market value of XX
        ]
        
        let foundPrice: string | null = null
        for (const pattern of pricePatterns) {
          const matches = content.match(pattern)
          if (matches && matches.length > 0) {
            // Extract the number from the match
            const numberMatch = matches[0].match(/\d+(?:\.\d{2})?/)
            if (numberMatch) {
              foundPrice = numberMatch[0]
              break
            }
          }
        }
        
        if (foundPrice) {
          setWebValue(`€${foundPrice}`)
        } else {
          setWebValue('No price found')
        }
      } else {
        setWebValue('Error fetching value')
      }
    } catch (error) {
      console.error('Error checking value:', error)
      setWebValue('Error')
    } finally {
      setIsCheckingValue(false)
    }
  }
  
  const applyWebValue = async () => {
    if (!webValue || !record?.record_id || webValue.includes('Error') || webValue === 'No price found') return
    
    try {
      // Extract number from webValue (e.g., "€50" -> "50")
      const priceMatch = webValue.match(/\d+(?:\.\d{2})?/)
      if (!priceMatch) return
      
      const newValue = parseFloat(priceMatch[0])
      
      // Update metadata with new value
      const updatedRecord = {
        ...record,
        metadata: {
          ...record.metadata,
          estimated_value_eur: newValue,
        },
      }
      
      onMetadataUpdate?.(updatedRecord.metadata)
      setWebValue(null)
    } catch (error) {
      console.error('Error applying web value:', error)
    }
  }

  const handleRegisterAction = async () => {
    if (!record) return
    
    const estimatedValue = getEstimatedValue()
    const condition = getCondition()
    
    // Use edited spotify_url if available, otherwise use record metadata
    const spotifyUrlToSave = editData.spotify_url || record.metadata?.spotify_url || undefined
    
    try {
      if (isInRegister) {
        // Update existing record in register
        await registerApiClient.updateRegisterRecord({
          record_id: record.record_id,
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
        
        // Add to register
        await registerApiClient.addToRegister({
          record_id: record.record_id,
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
      
    } catch (error) {
      console.error('Register operation failed:', error)
      alert('Failed to update register. Please try again.')
    }
  }

  const handleCancel = () => {
    setIsEditing(false)
    setEditData({ artist: '', title: '', year: '', label: '', spotify_url: '', catalog_number: '', barcode: '', genres: '' })
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
          <h4>Images ({uploadedImages.length + (record.metadata?.image_urls?.length || 0)})</h4>
          <div className={styles.imageGrid}>
            {/* Display images from database (loaded from register) */}
            {record.metadata?.image_urls?.map((imageUrl: string, index: number) => (
              <div key={`db-${index}`} className={styles.imageItem}>
                <img 
                  src={`${API_BASE}${imageUrl}`} 
                  alt={`Record image ${index + 1}`}
                  className={styles.image}
                />
              </div>
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
              onClick={() => onReanalyze(uploadedImages)}
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
          </div>
        ) : (
          <div className={styles.metadataEdit}>
            <div className={styles.field}>
              <label>Artist</label>
              <input 
                type="text" 
                value={editData.artist}
                onChange={(e) => setEditData(prev => ({...prev, artist: e.target.value}))}
              />
            </div>
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
              title="Get current market value from web"
            >
              {isCheckingValue ? '🔄' : '🌐'} {isCheckingValue ? 'Checking...' : 'Recheck Value'}
            </button>
          </h4>
          <div className={styles.valueContent}>
            <div className={styles.valueAmount}>
              €{getEstimatedValue()}
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
            {getCondition() && (
              <div className={styles.conditionBadge}>
                <span 
                  className={styles.conditionLabel}
                  style={{ color: getConditionColor() }}
                >
                  ● {getCondition()}
                </span>
                <small>Based on image analysis</small>
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
    </div>
  )
}