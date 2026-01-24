import { useRef, useState } from 'react'
import styles from './ImageUpload.module.css'

interface ImageUploadProps {
  onUpload: (files: File[]) => void
}

export default function ImageUpload({ onUpload }: ImageUploadProps) {
  const [preview, setPreview] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    
    if (files.length < 1 || files.length > 5) {
      alert('Please select between 1 and 5 images')
      return
    }

    const previews: string[] = []
    let loadedCount = 0

    files.forEach(file => {
      const reader = new FileReader()
      reader.onload = (event) => {
        previews.push(event.target?.result as string)
        loadedCount++

        if (loadedCount === files.length) {
          setPreview(previews)
        }
      }
      reader.readAsDataURL(file)
    })
  }

  const handleUpload = () => {
    if (fileInputRef.current?.files) {
      const files = Array.from(fileInputRef.current.files)
      onUpload(files)
    }
  }

  const handleClear = () => {
    setPreview([])
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
        
        {preview.length === 0 ? (
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
            <p>📸 Click to upload or drag and drop</p>
            <p className={styles.hint}>PNG, JPG, GIF up to 10MB (1-5 images)</p>
          </div>
        ) : (
          <div className={styles.previewGrid}>
            {preview.map((src, idx) => (
              <img
                key={idx}
                src={src}
                alt={`Preview ${idx + 1}`}
                className={styles.preview}
              />
            ))}
          </div>
        )}
      </div>

      {preview.length > 0 && (
        <div className={styles.actions}>
          <button onClick={handleUpload} className={styles.uploadBtn}>
            Upload {preview.length} Image{preview.length !== 1 ? 's' : ''}
          </button>
          <button onClick={handleClear} className={styles.clearBtn}>
            Clear
          </button>
        </div>
      )}
    </div>
  )
}
