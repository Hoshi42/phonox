import styles from './AnalysisModal.module.css'

export interface AnalysisResult {
  artist?: string
  title?: string
  year?: number
  label?: string
  catalog_number?: string
  genres?: string[]
  confidence?: number
}

export interface AnalysisModalProps {
  isOpen: boolean
  newAnalysis: AnalysisResult | null
  currentMetadata: AnalysisResult
  onAccept: () => void
  onReject: () => void
  isLoading?: boolean
}

export default function AnalysisModal({
  isOpen,
  newAnalysis,
  currentMetadata,
  onAccept,
  onReject,
  isLoading = false,
}: AnalysisModalProps) {
  if (!isOpen || !newAnalysis) return null

  const getChangedFields = () => {
    const changes = []
    
    if (newAnalysis.artist !== currentMetadata.artist) {
      changes.push({
        field: 'Artist',
        old: currentMetadata.artist || 'Not identified',
        new: newAnalysis.artist || 'Not identified',
      })
    }
    
    if (newAnalysis.title !== currentMetadata.title) {
      changes.push({
        field: 'Title',
        old: currentMetadata.title || 'Not identified',
        new: newAnalysis.title || 'Not identified',
      })
    }
    
    if (newAnalysis.year !== currentMetadata.year) {
      changes.push({
        field: 'Year',
        old: currentMetadata.year || 'Not identified',
        new: newAnalysis.year || 'Not identified',
      })
    }
    
    if (newAnalysis.label !== currentMetadata.label) {
      changes.push({
        field: 'Label',
        old: currentMetadata.label || 'Not identified',
        new: newAnalysis.label || 'Not identified',
      })
    }
    
    if (newAnalysis.catalog_number !== currentMetadata.catalog_number) {
      changes.push({
        field: 'Catalog Number',
        old: currentMetadata.catalog_number || 'Not identified',
        new: newAnalysis.catalog_number || 'Not identified',
      })
    }
    
    const oldGenres = currentMetadata.genres?.join(', ') || 'Not identified'
    const newGenres = newAnalysis.genres?.join(', ') || 'Not identified'
    if (oldGenres !== newGenres) {
      changes.push({
        field: 'Genres',
        old: oldGenres,
        new: newGenres,
      })
    }
    
    return changes
  }

  const changes = getChangedFields()
  const confidencePercent = newAnalysis.confidence
    ? Math.round(newAnalysis.confidence * 100)
    : 0

  return (
    <div className={styles.overlay} onClick={onReject}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeButton} onClick={onReject}>
          ✕
        </button>

        <h2>Analysis Results</h2>

        <div className={styles.confidenceSection}>
          <p className={styles.confidenceLabel}>Confidence Score</p>
          <div className={styles.confidenceBar}>
            <div
              className={styles.confidenceFill}
              style={{ width: `${confidencePercent}%` }}
            ></div>
            <span className={styles.confidenceText}>{confidencePercent}%</span>
          </div>
        </div>

        {changes.length > 0 ? (
          <div className={styles.changesSection}>
            <h3>Changes to Metadata</h3>
            <div className={styles.changesList}>
              {changes.map((change, idx) => (
                <div key={idx} className={styles.changeItem}>
                  <div className={styles.changeLabel}>{change.field}</div>
                  <div className={styles.changeComparison}>
                    <div className={styles.oldValue}>
                      <span className={styles.oldLabel}>Current:</span>
                      <span>{change.old}</span>
                    </div>
                    <div className={styles.arrow}>→</div>
                    <div className={styles.newValue}>
                      <span className={styles.newLabel}>New:</span>
                      <span>{change.new}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className={styles.noChanges}>
            <p>✓ No changes to metadata from this analysis</p>
          </div>
        )}

        <div className={styles.actions}>
          <button
            className={styles.rejectButton}
            onClick={onReject}
            disabled={isLoading}
          >
            Reject
          </button>
          <button
            className={styles.acceptButton}
            onClick={onAccept}
            disabled={isLoading}
          >
            {isLoading ? 'Applying...' : 'Accept Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}
