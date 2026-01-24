import { useState } from 'react'
import styles from './ReviewForm.module.css'

interface ReviewFormProps {
  recordId: string
  onReview: (corrections: Record<string, unknown>) => void
}

export default function ReviewForm({ onReview }: ReviewFormProps) {
  const [formData, setFormData] = useState({
    artist: '',
    title: '',
    year: '',
    label: '',
    catalog_number: '',
    genres: '',
    notes: '',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const corrections: Record<string, unknown> = {}
    
    Object.entries(formData).forEach(([key, value]) => {
      if (value) {
        if (key === 'genres') {
          corrections[key] = value.split(',').map(g => g.trim()).filter(Boolean)
        } else if (key === 'year') {
          corrections[key] = parseInt(value, 10)
        } else {
          corrections[key] = value
        }
      }
    })

    onReview(corrections)
  }

  return (
    <div className={styles.reviewContainer}>
      <h3>Manual Review & Corrections</h3>
      <p className={styles.subtitle}>
        The AI is uncertain about some details. Please review and correct as needed.
      </p>

      <form onSubmit={handleSubmit}>
        <div className={styles.formGroup}>
          <label htmlFor="artist">Artist</label>
          <input
            type="text"
            id="artist"
            name="artist"
            value={formData.artist}
            onChange={handleChange}
            placeholder="Enter artist name"
          />
        </div>

        <div className={styles.formGroup}>
          <label htmlFor="title">Title</label>
          <input
            type="text"
            id="title"
            name="title"
            value={formData.title}
            onChange={handleChange}
            placeholder="Enter album title"
          />
        </div>

        <div className={styles.formGroup}>
          <label htmlFor="year">Year</label>
          <input
            type="number"
            id="year"
            name="year"
            value={formData.year}
            onChange={handleChange}
            placeholder="YYYY"
            min="1900"
            max={new Date().getFullYear()}
          />
        </div>

        <div className={styles.formGroup}>
          <label htmlFor="label">Label</label>
          <input
            type="text"
            id="label"
            name="label"
            value={formData.label}
            onChange={handleChange}
            placeholder="Enter record label"
          />
        </div>

        <div className={styles.formGroup}>
          <label htmlFor="catalog_number">Catalog Number</label>
          <input
            type="text"
            id="catalog_number"
            name="catalog_number"
            value={formData.catalog_number}
            onChange={handleChange}
            placeholder="Enter catalog number"
          />
        </div>

        <div className={styles.formGroup}>
          <label htmlFor="genres">Genres</label>
          <input
            type="text"
            id="genres"
            name="genres"
            value={formData.genres}
            onChange={handleChange}
            placeholder="Comma-separated genres (e.g., Rock, Jazz, Pop)"
          />
        </div>

        <div className={styles.formGroup}>
          <label htmlFor="notes">Additional Notes</label>
          <textarea
            id="notes"
            name="notes"
            value={formData.notes}
            onChange={handleChange}
            placeholder="Any additional information or corrections"
            rows={3}
          />
        </div>

        <button type="submit" className={styles.submitBtn}>
          Submit Corrections
        </button>
      </form>
    </div>
  )
}
