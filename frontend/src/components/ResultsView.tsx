import { VinylRecord } from '../App'
import styles from './ResultsView.module.css'

interface ResultsViewProps {
  record: VinylRecord
}

export default function ResultsView({ record }: ResultsViewProps) {
  const confidenceColor = record.confidence >= 0.85 ? 'green' : record.confidence >= 0.6 ? 'orange' : 'red'

  return (
    <div className={styles.resultsContainer}>
      <div className={styles.header}>
        <h2>Analysis Results</h2>
        {record.auto_commit && (
          <span className={styles.autoApprovedBadge}>✓ Auto-Approved</span>
        )}
        {record.needs_review && (
          <span className={styles.reviewBadge}>⚠ Needs Review</span>
        )}
      </div>

      <div className={styles.metadata}>
        <div className={styles.field}>
          <label>Artist</label>
          <p>{record.artist || 'Not identified'}</p>
        </div>

        <div className={styles.field}>
          <label>Title</label>
          <p>{record.title || 'Not identified'}</p>
        </div>

        <div className={styles.field}>
          <label>Year</label>
          <p>{record.year || 'Not identified'}</p>
        </div>

        <div className={styles.field}>
          <label>Label</label>
          <p>{record.label || 'Not identified'}</p>
        </div>

        <div className={styles.field}>
          <label>Catalog Number</label>
          <p>{record.catalog_number || 'Not identified'}</p>
        </div>

        {record.genres && record.genres.length > 0 && (
          <div className={styles.field}>
            <label>Genres</label>
            <div className={styles.genres}>
              {record.genres.map((genre, idx) => (
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
