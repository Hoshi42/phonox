import { useEffect, useState } from 'react'
import styles from './App.module.css'
import LoadingSpinner from './components/LoadingSpinner'
import ChatPanel from './components/ChatPanel'
import VinylCard from './components/VinylCard'
import VinylRegister from './components/VinylRegister'
import { apiClient } from './api/client'
import { registerApiClient, RegisterRecord } from './services/registerApi'

// Environment configuration
const POLL_INTERVAL = parseInt(import.meta.env.VITE_POLL_INTERVAL || '2000', 10)

export interface VinylRecord {
  record_id: string
  id?: string
  status: string
  artist?: string
  title?: string
  year?: number
  label?: string
  catalog_number?: string
  genres?: string[]
  confidence: number
  auto_commit: boolean
  needs_review: boolean
  evidence_chain: unknown[]
  error?: string
  metadata?: {
    artist?: string
    title?: string
    year?: number
    label?: string
    spotify_url?: string
    catalog_number?: string
    genres?: string[]
    estimated_value_eur?: number
  }
  created_at?: string
  updated_at?: string
  user_notes?: string | null
}

function App() {
  const [recordId, setRecordId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [record, setRecord] = useState<VinylRecord | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pollInterval, setPollInterval] = useState<any>(null)
  const [uploadedImages, setUploadedImages] = useState<File[]>([])
  const [vinylRegister, setVinylRegister] = useState<RegisterRecord[]>([])
  const [showRegister, setShowRegister] = useState(false)
  const [registerLoading, setRegisterLoading] = useState(false)

  const handleUpload = async (files: File[]) => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.identify(files)
      const newRecordId = response.record_id
      setRecordId(newRecordId)
      setUploadedImages(files)

      // Start polling for results
      const interval = setInterval(async () => {
        try {
          const statusResponse = await apiClient.getResult(newRecordId)
          
          if (statusResponse.status === 'complete' || statusResponse.status === 'error') {
            clearInterval(interval)
            setLoading(false)
            setPollInterval(null)
            
            if (statusResponse.status === 'complete') {
              setRecord(statusResponse as unknown as VinylRecord)
            } else {
              setError((statusResponse as any).error || 'Analysis failed')
            }
          }
        } catch (err) {
          clearInterval(interval)
          setLoading(false)
          setPollInterval(null)
          setError('Failed to get analysis status')
        }
      }, POLL_INTERVAL)

      setPollInterval(interval)
    } catch (err) {
      setLoading(false)
      setError('Upload failed. Please try again.')
    }
  }

  const handleMetadataUpdate = (metadata: any) => {
    if (record) {
      setRecord(prev => prev ? {
        ...prev,
        metadata: {
          ...prev.metadata,
          ...metadata
        }
      } : null)
    }
  }

  const handleImageAdd = (newFiles: FileList) => {
    const filesArray = Array.from(newFiles)
    const totalImages = uploadedImages.length + filesArray.length
    
    if (totalImages > 5) {
      alert('Maximum 5 images allowed')
      return
    }
    
    setUploadedImages(prev => [...prev, ...filesArray])
    
    // If we have a record, trigger re-analysis with new images
    if (record) {
      handleUpload([...uploadedImages, ...filesArray])
    } else {
      // If no record yet, start initial analysis
      handleUpload(filesArray)
    }
  }

  const handleImageRemove = (index: number) => {
    setUploadedImages(prev => prev.filter((_, i) => i !== index))
  }

  const handleAddToRegister = async (record: VinylRecord) => {
    // The actual API call is handled in VinylCard component
    // This just triggers a reload of the register
    await loadRegister()
  }

  const handleUpdateRegister = async (record: VinylRecord) => {
    // The actual API call is handled in VinylCard component
    // This just triggers a reload of the register
    await loadRegister()
  }

  const handleDeleteFromRegister = async (recordId: string) => {
    try {
      await registerApiClient.removeFromRegister(recordId)
      await loadRegister()
    } catch (error) {
      console.error('Failed to remove from register:', error)
      alert('Failed to remove record from register. Please try again.')
    }
  }

  const handleRecordSelectFromRegister = (registerRecord: RegisterRecord) => {
    // Convert RegisterRecord to VinylRecord format
    const vinylRecord: VinylRecord = {
      record_id: registerRecord.id,
      id: registerRecord.id,
      status: 'complete',
      artist: registerRecord.artist,
      title: registerRecord.title,
      year: registerRecord.year,
      label: registerRecord.label,
      catalog_number: registerRecord.catalog_number,
      genres: registerRecord.genres,
      confidence: registerRecord.confidence || 0,
      auto_commit: false,
      needs_review: false,
      evidence_chain: [],
      metadata: {
        artist: registerRecord.artist,
        title: registerRecord.title,
        year: registerRecord.year,
        label: registerRecord.label,
        spotify_url: registerRecord.spotify_url,
        catalog_number: registerRecord.catalog_number,
        genres: registerRecord.genres,
        estimated_value_eur: registerRecord.estimated_value_eur,
        image_urls: registerRecord.image_urls || [],
      },
      created_at: registerRecord.created_at,
      updated_at: registerRecord.updated_at,
      user_notes: registerRecord.user_notes,
    }

    // Set the record in the main view
    setRecord(vinylRecord)
    setRecordId(registerRecord.id)
    // Clear any existing images since we're loading from register
    setUploadedImages([])
    // Close the register view
    setShowRegister(false)
  }

  const isRecordInRegister = record ? 
    vinylRegister.some(r => r.id === record.record_id) : false

  // Load register from database on component mount
  useEffect(() => {
    loadRegister()
  }, [])

  const loadRegister = async () => {
    setRegisterLoading(true)
    try {
      const registerData = await registerApiClient.getRegister()
      setVinylRegister(registerData)
    } catch (error) {
      console.error('Failed to load register:', error)
    } finally {
      setRegisterLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1 className={styles.title}>
            🎵 Phonox
          </h1>
          <p className={styles.subtitle}>
            AI-powered vinyl record identification with web search
          </p>
        </div>
        <button 
          className={styles.registerButton}
          onClick={() => setShowRegister(true)}
        >
          📚 My Register ({vinylRegister.length})
        </button>
      </header>

      <main className={styles.main}>
        <div className={styles.chatContainer}>
          <ChatPanel
            record={record}
            onImageUpload={handleUpload}
            onAnalysisComplete={() => {}}
            onMetadataUpdate={handleMetadataUpdate}
          />
        </div>
        
        <div className={styles.cardContainer}>
          <VinylCard
            record={record}
            uploadedImages={uploadedImages}
            onMetadataUpdate={handleMetadataUpdate}
            onImageAdd={handleImageAdd}
            onImageRemove={handleImageRemove}
            onAddToRegister={handleAddToRegister}
            onUpdateRegister={handleUpdateRegister}
            onRegisterSuccess={loadRegister}
            isInRegister={isRecordInRegister}
          />
        </div>
      </main>

      {showRegister && (
        <VinylRegister
          records={vinylRegister}
          onClose={() => setShowRegister(false)}
          onDeleteRecord={handleDeleteFromRegister}
          onRecordSelect={handleRecordSelectFromRegister}
        />
      )}

      {loading && (
        <div className={styles.loadingOverlay}>
          <div className={styles.loadingContent}>
            <LoadingSpinner />
            <p>Analyzing your vinyl record images...</p>
          </div>
        </div>
      )}

      {error && (
        <div className={styles.errorOverlay}>
          <div className={styles.errorContent}>
            <h3>Error</h3>
            <p>{error}</p>
            <button 
              onClick={() => setError(null)}
              className={styles.errorCloseBtn}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default App