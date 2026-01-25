import { useState } from 'react'
import { VinylRecord } from '../App'
import styles from './ResultsView.module.css'

interface ResultsViewProps {
  record: VinylRecord
  uploadedImages?: File[]
  onRedoRecognition?: () => void
  onImagesChange?: (images: File[]) => void
  onAnalyzeSingle?: (file: File, imageId: string) => void
}

interface UploadedImageInfo {
  id: string
  file: File
  preview: string
  analyzed: boolean
}

export default function ResultsView({ 
  record, 
  uploadedImages = [], 
  onRedoRecognition,
  onImagesChange,
  onAnalyzeSingle
}: ResultsViewProps) {
  const [showRawData, setShowRawData] = useState(false)
  const [images, setImages] = useState<UploadedImageInfo[]>(
    uploadedImages.map((file, idx) => ({
      id: `${idx}-${Date.now()}`,
      file,
      preview: URL.createObjectURL(file),
      analyzed: false,
    }))
  )

  // Extract metadata from nested structure or flat fields
  const metadata = record.metadata || {}
  const artist = metadata.artist || record.artist || 'Not identified'
  const title = metadata.title || record.title || 'Not identified'
  const year = metadata.year || record.year || 'Not identified'
  const label = metadata.label || record.label || 'Not identified'
  const catalog_number = metadata.catalog_number || record.catalog_number || 'Not identified'
  const genres = metadata.genres || record.genres || []

  const confidenceColor = record.confidence >= 0.85 ? 'green' : record.confidence >= 0.6 ? 'orange' : 'red'

  const handleRemoveImage = (imageId: string) => {
    const updatedImages = images.filter(img => img.id !== imageId)
    setImages(updatedImages)
    onImagesChange?.(updatedImages.map(img => img.file))
  }

  const handleAddImages = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.currentTarget.files || [])
    const currentCount = images.length
    const available = 5 - currentCount
    const toAdd = files.slice(0, available)

    const newImages = toAdd.map((file, idx) => ({
      id: `${currentCount + idx}-${Date.now()}`,
      file,
      preview: URL.createObjectURL(file),
      analyzed: false,
    }))

    const combined = [...images, ...newImages]
    setImages(combined)
    onImagesChange?.(combined.map(img => img.file))
    
    // Reset input
    e.currentTarget.value = ''
  }

  const handleAnalyzeImage = async (image: UploadedImageInfo) => {
    if (onAnalyzeSingle) {
      onAnalyzeSingle(image.file, image.id)
      setImages(prev => prev.map(img => 
        img.id === image.id ? { ...img, analyzed: true } : img
      ))
    }
  }

  return (
    <div className={styles.resultsContainer}>
      {images && images.length > 0 && (
        <div className={styles.imagesSection}>
          <div className={styles.imagesHeader}>
            <h3>Bilder ({images.length}/5)</h3>
            {images.length < 5 && (
              <label className={styles.addImagesLabel}>
                <input
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={handleAddImages}
                  style={{ display: 'none' }}
                />
                + Bilder hinzufügen
              </label>
            )}
          </div>
          <div className={styles.imageGrid}>
            {images.map((image) => (
              <div key={image.id} className={styles.imageCard}>
                <div className={styles.imageWrapper}>
                  <img
                    src={image.preview}
                    alt="Vinyl"
                    className={styles.image}
                  />
                  {image.analyzed && (
                    <div className={styles.analyzedBadge}>✓</div>
                  )}
                </div>
                <div className={styles.imageActions}>
                  {!image.analyzed && (
                    <button
                      className={styles.analyzeBtn}
                      onClick={() => handleAnalyzeImage(image)}
                      title="Bild analysieren"
                    >
                      📊
                    </button>
                  )}
                  <button
                    className={styles.deleteBtn}
                    onClick={() => handleRemoveImage(image.id)}
                    title="Bild entfernen"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h2>Analysis Results</h2>
          <p className={styles.modelInfo}>Vision: Claude Sonnet 4.5</p>
        </div>
        <div className={styles.headerRight}>
          {record.auto_commit && (
            <span className={styles.autoApprovedBadge}>✓ Auto-Approved</span>
          )}
          {record.needs_review && (
            <span className={styles.reviewBadge}>⚠ Needs Review</span>
          )}
        </div>
      </div>

      {onRedoRecognition && (
        <div className={styles.actionBar}>
          <button className={styles.redoButton} onClick={onRedoRecognition}>
            🔄 Redo Recognition
          </button>
        </div>
      )}

      <div className={styles.metadata}>
        <div className={styles.field}>
          <label>Artist</label>
          <p>{artist}</p>
        </div>

        <div className={styles.field}>
          <label>Title</label>
          <p>{title}</p>
        </div>

        <div className={styles.field}>
          <label>Year</label>
          <p>{year}</p>
        </div>

        <div className={styles.field}>
          <label>Label</label>
          <p>{label}</p>
        </div>

        <div className={styles.field}>
          <label>Catalog Number</label>
          <p>{catalog_number}</p>
        </div>

        {genres && genres.length > 0 && (
          <div className={styles.field}>
            <label>Genres</label>
            <div className={styles.genres}>
              {genres.map((genre, idx) => (
                <span key={idx} className={styles.genre}>
                  {genre}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className={styles.field}>
          <label>Confidence Score</label>
          <div className={styles.confidenceBar}>
            <div
              className={styles.confidenceFill}
              style={{
                width: `${Math.round(record.confidence * 100)}%`,
                backgroundColor: confidenceColor,
              }}
            ></div>
            <span className={styles.confidenceText}>
              {Math.round(record.confidence * 100)}%
            </span>
          </div>
        </div>
      </div>

      {record.evidence_chain && record.evidence_chain.length > 0 && (
        <div className={styles.evidence}>
          <h3>Evidence Chain</h3>
          <div className={styles.evidenceItems}>
            {(record.evidence_chain as any[]).map((evidence, idx) => (
              <div key={idx} className={styles.evidenceItem}>
                <span className={styles.evidenceSource}>{evidence.source}</span>
                <span className={styles.evidenceConfidence}>
                  {Math.round(evidence.confidence * 100)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className={styles.rawDataSection}>
        <button
          className={styles.rawDataToggle}
          onClick={() => setShowRawData(!showRawData)}
        >
          {showRawData ? '▼' : '▶'} Raw Data
        </button>
        
        {showRawData && (
          <div className={styles.rawDataPanel}>
            <pre className={styles.rawDataContent}>
              {JSON.stringify(record, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {record.error && (
        <div className={styles.error}>
          <strong>Error:</strong> {record.error}
        </div>
      )}

      {record.status === 'failed' && (
        <div className={styles.failed}>
          <p>Failed to process images. Please try again.</p>
        </div>
      )}
    </div>
  )
}
