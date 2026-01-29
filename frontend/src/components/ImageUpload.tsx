import { useRef, useState } from 'react'
import styles from './ImageUpload.module.css'

export interface UploadedImage {
  id: string
  file: File
  preview: string
  analyzed: boolean
  uploadStatus?: 'pending' | 'uploading' | 'success' | 'error'
  uploadError?: string
}

interface ImageUploadProps {
  onUpload: (files: File[], condition?: string) => void
  onAnalyzeSingle?: (file: File, imageId: string) => void
}

const MAX_RETRIES = 3
const RETRY_DELAY = 1000 // ms

export default function ImageUpload({ onUpload, onAnalyzeSingle }: ImageUploadProps) {
  const [images, setImages] = useState<UploadedImage[]>([])
  const [condition, setCondition] = useState('good')
  const [uploading, setUploading] = useState(false)
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
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        alert(`File ${file.name} is too large (max 10MB)`)
        return
      }

      // Validate file type
      if (!file.type.startsWith('image/')) {
        alert(`File ${file.name} is not a valid image`)
        return
      }

      const reader = new FileReader()
      reader.onload = (event) => {
        newImages.push({
          id: `img_${Date.now()}_${Math.random()}`,
          file,
          preview: event.target?.result as string,
          analyzed: false,
          uploadStatus: 'pending',
        })
        loadedCount++

        if (loadedCount === files.length) {
          setImages([...images, ...newImages])
        }
      }
      reader.onerror = () => {
        alert(`Failed to read file ${file.name}`)
        loadedCount++
      }
      reader.readAsDataURL(file)
    })
  }

  const handleRemoveImage = (id: string) => {
    setImages(images.filter(img => img.id !== id))
  }

  const handleAnalyzeSingle = (image: UploadedImage) => {
    if (onAnalyzeSingle) {
      // Update status to uploading
      setImages(images.map(img => 
        img.id === image.id ? { ...img, uploadStatus: 'uploading' } : img
      ))
      
      // Try to upload with retries
      retryUpload(() => onAnalyzeSingle(image.file, image.id), image.id)
        .then(() => {
          // Mark as analyzed after successful send
          setImages(images.map(img => 
            img.id === image.id ? { ...img, analyzed: true, uploadStatus: 'success' } : img
          ))
        })
        .catch((error) => {
          setImages(images.map(img => 
            img.id === image.id ? { ...img, uploadStatus: 'error', uploadError: error.message } : img
          ))
        })
    }
  }

  const handleAnalyzeAll = async () => {
    const files = images.map(img => img.file)
    
    if (files.length === 0) return
    
    setUploading(true)
    
    // Mark all as uploading
    setImages(images.map(img => ({ ...img, uploadStatus: 'uploading' })))
    
    try {
      // Retry upload logic
      await retryUpload(() => onUpload(files, condition))
      
      // Mark all as analyzed after successful send
      setImages(images.map(img => ({ ...img, analyzed: true, uploadStatus: 'success' })))
    } catch (error: any) {
      const errorMessage = error.message || 'Upload failed'
      setImages(images.map(img => ({ ...img, uploadStatus: 'error', uploadError: errorMessage })))
      alert(`Upload failed: ${errorMessage}. Please try again.`)
    } finally {
      setUploading(false)
    }
  }

  const retryUpload = async (
    uploadFn: () => void | Promise<void>,
    imageId?: string,
    retryCount = 0
  ): Promise<void> => {
    try {
      await Promise.resolve(uploadFn())
      return
    } catch (error: any) {
      if (retryCount < MAX_RETRIES) {
        // Exponential backoff: 1s, 2s, 4s
        const delay = RETRY_DELAY * Math.pow(2, retryCount)
        console.warn(`Upload attempt ${retryCount + 1} failed, retrying in ${delay}ms...`, error)
        
        await new Promise(resolve => setTimeout(resolve, delay))
        return retryUpload(uploadFn, imageId, retryCount + 1)
      } else {
        throw new Error(`Upload failed after ${MAX_RETRIES} attempts: ${error.message}`)
      }
    }
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
          disabled={uploading}
        />
        
        {images.length === 0 ? (
          <div
            className={styles.dragArea}
            onClick={() => !uploading && fileInputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault()
              if (!uploading) e.currentTarget.classList.add(styles.dragActive)
            }}
            onDragLeave={(e) => e.currentTarget.classList.remove(styles.dragActive)}
            onDrop={(e) => {
              e.preventDefault()
              if (uploading) return
              e.currentTarget.classList.remove(styles.dragActive)
              if (fileInputRef.current) {
                fileInputRef.current.files = e.dataTransfer.files
                const event = new Event('change', { bubbles: true })
                fileInputRef.current.dispatchEvent(event)
              }
            }}
            style={{ opacity: uploading ? 0.5 : 1, cursor: uploading ? 'not-allowed' : 'pointer' }}
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
                  {image.uploadStatus === 'uploading' && (
                    <div className={styles.uploadingBadge}>⏳</div>
                  )}
                  {image.uploadStatus === 'success' && (
                    <div className={styles.analyzedBadge}>✓</div>
                  )}
                  {image.uploadStatus === 'error' && (
                    <div className={styles.errorBadge} title={image.uploadError}>❌</div>
                  )}
                </div>
                <div className={styles.imageActions}>
                  {onAnalyzeSingle && !image.analyzed && image.uploadStatus !== 'uploading' && (
                    <button
                      onClick={() => handleAnalyzeSingle(image)}
                      className={styles.analyzeBtn}
                      title="Dieses Bild analysieren"
                      disabled={uploading}
                    >
                      📊 Analyse
                    </button>
                  )}
                  <button
                    onClick={() => handleRemoveImage(image.id)}
                    className={styles.removeBtn}
                    title="Bild entfernen"
                    disabled={uploading || image.uploadStatus === 'uploading'}
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
              disabled={uploading}
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
          {onAnalyzeSingle && images.some(img => !img.analyzed && img.uploadStatus !== 'uploading') && (
            <button 
              onClick={handleAnalyzeAll} 
              className={styles.uploadBtn}
              disabled={uploading}
            >
              {uploading ? '⏳ Wird hochgeladen...' : `Alle ${images.filter(img => !img.analyzed).length} analysieren`}
            </button>
          )}
          {!onAnalyzeSingle && (
            <button 
              onClick={handleAnalyzeAll} 
              className={styles.uploadBtn}
              disabled={uploading}
            >
              {uploading ? '⏳ Wird hochgeladen...' : `${images.length} Bild${images.length !== 1 ? 'er' : ''} analysieren`}
            </button>
          )}
          <button 
            onClick={handleClear} 
            className={styles.clearBtn}
            disabled={uploading}
          >
            Löschen
          </button>
        </div>
      )}
    </div>
  )
}

