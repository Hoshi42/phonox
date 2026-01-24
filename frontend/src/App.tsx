import { useState } from 'react'
import styles from './App.module.css'
import ImageUpload from './components/ImageUpload'
import LoadingSpinner from './components/LoadingSpinner'
import ResultsView from './components/ResultsView'
import ReviewForm from './components/ReviewForm'
import ChatPanel from './components/ChatPanel'
import { apiClient } from './api/client'

// Environment configuration
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const POLL_INTERVAL = parseInt(import.meta.env.VITE_POLL_INTERVAL || '2000', 10)

export interface VinylRecord {
  id: string
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
}

function App() {
  const [recordId, setRecordId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [record, setRecord] = useState<VinylRecord | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null)

  const handleUpload = async (files: File[]) => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.identify(files)
      setRecordId(response.id)
      
      // Start polling for results
      const interval = setInterval(async () => {
        try {
          const result = await apiClient.getResult(response.id)
          setRecord(result)
          
          if (result.status === 'complete' || result.status === 'failed') {
            clearInterval(interval)
            setLoading(false)
          }
        } catch (err) {
          console.error('Polling error:', err)
        }
      }, 2000)
      
      setPollInterval(interval)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setLoading(false)
    }
  }

  const handleReview = async (corrections: Record<string, unknown>) => {
    if (!recordId) return
    
    setLoading(true)
    setError(null)
    try {
      const updated = await apiClient.review(recordId, corrections)
      setRecord(updated)
      setLoading(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Review submission failed')
      setLoading(false)
    }
  }

  const handleReset = () => {
    setRecordId(null)
    setRecord(null)
    setError(null)
    setLoading(false)
    if (pollInterval) {
      clearInterval(pollInterval)
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Phonox - Vinyl Record Identifier</h1>
        <p>Upload images of your vinyl records for AI-powered identification</p>
      </header>

      <div className={styles.mainWrapper}>
        <main className={styles.main}>
          {error && (
            <div className={styles.error}>
              <button onClick={() => setError(null)}>&times;</button>
              {error}
            </div>
          )}

          {!record && !loading && (
            <ImageUpload onUpload={handleUpload} />
          )}

          {loading && <LoadingSpinner />}

          {record && (
            <>
              <ResultsView record={record} />
              
              {record.needs_review && !record.auto_commit && (
                <ReviewForm recordId={recordId || ''} onReview={handleReview} />
              )}
              
              <button onClick={handleReset} className={styles.resetButton}>
                Identify Another Record
              </button>
            </>
          )}
        </main>

        {recordId && record && (
          <aside className={styles.chatSidebar}>
            <ChatPanel
              recordId={recordId}
              currentMetadata={{
                artist: record.artist,
                title: record.title,
                year: record.year,
                label: record.label,
                catalog_number: record.catalog_number,
                genres: record.genres,
              }}
              onMetadataUpdate={(metadata) => {
                setRecord((prev) =>
                  prev
                    ? {
                        ...prev,
                        artist: (metadata.artist as string) || prev.artist,
                        title: (metadata.title as string) || prev.title,
                        year: (metadata.year as number) || prev.year,
                        label: (metadata.label as string) || prev.label,
                        catalog_number: (metadata.catalog_number as string) || prev.catalog_number,
                        genres: (metadata.genres as string[]) || prev.genres,
                      }
                    : null,
                )
              }}
              onClose={undefined}
            />
          </aside>
        )}
      </div>

      <footer className={styles.footer}>
        <p>&copy; 2024 Phonox. AI-powered vinyl record identification.</p>
      </footer>
    </div>
  )
}
}

export default App
