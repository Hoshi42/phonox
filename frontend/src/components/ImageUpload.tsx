import { useRef, useState } from 'react'
import styles from './ImageUpload.module.css'

export interface UploadedImage {
  id: string
  file: File
  preview: string
  analyzed: boolean
}

interface ImageUploadProps {
  onUpload: (files: File[], condition?: string) => void
  onAnalyzeSingle?: (file: File, imageId: string) => void
}

export default function ImageUpload({ onUpload, onAnalyzeSingle }: ImageUploadProps) {
  const [images, setImages] = useState<UploadedImage[]>([])
  const [condition, setCondition] = useState('good')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    
    if (files.length < 1) {
      alert('Please select at least 1 image')
      return
    }

    if (images.length + files.length > 5) {
      alert('Maximum 5 images allowed')
      return
    }

    let loadedCount = 0
    const newImages: UploadedImage[] = []

    files.forEach(file => {
      const reader = new FileReader()
      reader.onload = (event) => {
        newImages.push({
          id: `img_${Date.now()}_${Math.random()}`,
          file,
          preview: event.target?.result as string,
          analyzed: false,
        })
        loadedCount++

        if (loadedCount === files.length) {
          setImages([...images, ...newImages])
        }
      }
      reader.readAsDataURL(file)
    })
  }

  const handleRemoveImage = (id: string) => {
    setImages(images.filter(img => img.id !== id))
  }

  const handleAnalyzeSingle = (image: UploadedImage) => {
    if (onAnalyzeSingle) {
      onAnalyzeSingle(image.file, image.id)
      // Mark as analyzed after sending
      setImages(images.map(img => 
        img.id === image.id ? { ...img, analyzed: true } : img
      ))
    }
  }

  const handleAnalyzeAll = () => {
    const files = images.map(img => img.file)
    onUpload(files, condition)
    // Mark all as analyzed
    setImages(images.map(img => ({ ...img, analyzed: true })))
  }

  const handleClear = () => {
    setImages([])
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className={styles.uploadContainer}>
      <div className={styles.uploadBox}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileSelect}
          className={styles.fileInput}
          style={{ display: 'none' }}
        />
        
        {images.length === 0 ? (
          <div
            className={styles.dragArea}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              if (fileInputRef.current) {
                fileInputRef.current.files = e.dataTransfer.files
                const event = new Event('change', { bubbles: true })
                fileInputRef.current.dispatchEvent(event)
              }
            }}
          >
            <p>📸 Click oder Drag & Drop</p>
            <p className={styles.hint}>PNG, JPG, GIF bis 10MB (1-5 Bilder)</p>
          </div>
        ) : (
          <div className={styles.previewGrid}>
            {images.map((image) => (
              <div key={image.id} className={styles.imageCard}>
                <div className={styles.imageWrapper}>
                  <img
                    src={image.preview}
                    alt={`Preview`}
                    className={styles.preview}
                  />
                  {image.analyzed && (
                    <div className={styles.analyzedBadge}>✓</div>
                  )}
                </div>
                <div className={styles.imageActions}>
                  {onAnalyzeSingle && !image.analyzed && (
                    <button
                      onClick={() => handleAnalyzeSingle(image)}
                      className={styles.analyzeBtn}
                      title="Dieses Bild analysieren"
                    >
                      📊 Analyse
                    </button>
                  )}
                  <button
                    onClick={() => handleRemoveImage(image.id)}
                    className={styles.removeBtn}
                    title="Bild entfernen"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {images.length > 0 && (
        <div className={styles.actions}>
          <div className={styles.conditionField}>
            <label htmlFor="condition">Record Condition:</label>
            <select 
              id="condition"
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
              className={styles.conditionSelect}
            >
              <option value="mint">Mint (M)</option>
              <option value="near_mint">Near Mint (NM)</option>
              <option value="very_good_plus">Very Good+ (VG+)</option>
              <option value="very_good">Very Good (VG)</option>
              <option value="good_plus">Good+ (G+)</option>
              <option value="good">Good (G)</option>
              <option value="fair_plus">Fair+ (F+)</option>
              <option value="fair">Fair (F)</option>
              <option value="poor">Poor (P)</option>
            </select>
          </div>
          {onAnalyzeSingle && images.some(img => !img.analyzed) && (
            <button onClick={handleAnalyzeAll} className={styles.uploadBtn}>
              Alle {images.filter(img => !img.analyzed).length} analysieren
            </button>
          )}
          {!onAnalyzeSingle && (
            <button onClick={handleAnalyzeAll} className={styles.uploadBtn}>
              {images.length} Bild{images.length !== 1 ? 'er' : ''} analysieren
            </button>
          )}
          <button onClick={handleClear} className={styles.clearBtn}>
            Löschen
          </button>
        </div>
      )}
    </div>
  )
}
