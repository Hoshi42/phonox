import { useEffect, useState } from 'react'
import styles from './App.module.css'
import LoadingSpinner from './components/LoadingSpinner'
import ChatPanel from './components/ChatPanel'
import VinylCard from './components/VinylCard'
import VinylRegister from './components/VinylRegister'
import UserManager from './components/UserManager'
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
  barcode?: string  // UPC/EAN barcode
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
    barcode?: string  // UPC/EAN barcode
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
  const [currentUser, setCurrentUser] = useState('')

  const handleUpload = async (files: File[]) => {
    const previousRecord = record  // Preserve previous record for error recovery
    const previousRecordId = recordId
    
    try {
      console.log('App: Starting upload with', files.length, 'files')
      console.log('App: API Client base URL:', (apiClient as any).baseUrl || 'Unknown')
      console.log('App: Window location:', window.location.href)
      console.log('App: User Agent:', navigator.userAgent)
      console.log('App: Online status:', navigator.onLine)
      console.log('App: Environment VITE_API_URL:', import.meta.env.VITE_API_URL || 'Not set')
      setLoading(true)
      setError(null)

      const response = await apiClient.identify(files)
      const newRecordId = response.record_id
      console.log('App: Upload successful, record ID:', newRecordId)
      console.log('App: Initial response status:', response.status)
      setRecordId(newRecordId)
      setUploadedImages(files)

      // If already analyzed/complete from initial response, use it
      if (response.status === 'analyzed' || response.status === 'complete') {
        console.log('App: Analysis already complete from initial response, status:', response.status)
        const newRecord = response as unknown as VinylRecord
        setRecord(newRecord)
        setLoading(false)
        const timestamp = Date.now()
        localStorage.setItem('phonox_current_record', JSON.stringify(newRecord))
        localStorage.setItem('phonox_current_record_id', newRecordId)
        localStorage.setItem('phonox_cache_timestamp', timestamp.toString())
        return
      }

      // Start polling for results
      let pollCount = 0
      const maxPolls = 600 // 10 minutes with 1-second intervals
      const interval = setInterval(async () => {
        pollCount++
        try {
          const statusResponse = await apiClient.getResult(newRecordId)
          console.log(`App: Poll ${pollCount} - Status: ${statusResponse.status}`)
          
          if (statusResponse.status === 'analyzed' || statusResponse.status === 'complete' || statusResponse.status === 'failed' || statusResponse.status === 'error') {
            clearInterval(interval)
            setLoading(false)
            setPollInterval(null)
            console.log('App: Polling finished with status:', statusResponse.status)
            
            if (statusResponse.status === 'analyzed' || statusResponse.status === 'complete') {
              const newRecord = statusResponse as unknown as VinylRecord
              setRecord(newRecord)
              console.log('App: Analysis complete, record set')
              // Save to localStorage
              const timestamp = Date.now()
              localStorage.setItem('phonox_current_record', JSON.stringify(newRecord))
              localStorage.setItem('phonox_current_record_id', newRecordId)
              localStorage.setItem('phonox_cache_timestamp', timestamp.toString())
            } else {
              // Restore previous record if available
              if (previousRecord && previousRecordId) {
                setRecord(previousRecord)
                setRecordId(previousRecordId)
              }
              const errorMsg = statusResponse.error || statusResponse.message || 'Analysis failed'
              console.error('App: Analysis failed:', errorMsg)
              setError(`Analysis failed: ${errorMsg}`)
            }
          } else if (pollCount > maxPolls) {
            console.error('App: Polling timeout')
            clearInterval(interval)
            setLoading(false)
            setPollInterval(null)
            setError('Analysis timeout - please try again')
          }
        } catch (err) {
          console.error('App: Polling error:', err)
          console.error('App: Polling error details:', {
            message: err instanceof Error ? err.message : String(err),
            pollCount,
            maxPolls
          })
          // Don't clear interval on individual errors, keep polling
          if (pollCount > maxPolls) {
            clearInterval(interval)
            setLoading(false)
            setPollInterval(null)
            if (previousRecord && previousRecordId) {
              setRecord(previousRecord)
              setRecordId(previousRecordId)
            }
            const errorMsg = err instanceof Error ? err.message : 'Failed to get analysis status'
            console.error('App: Max polling attempts reached, error:', errorMsg)
            setError(errorMsg)
          }
        }
      }, 1000) // Poll every second for faster response

      setPollInterval(interval)
    } catch (err) {
      console.error('App: Upload failed:', err)
      console.error('App: Error details:', {
        name: err instanceof Error ? err.name : 'Unknown',
        message: err instanceof Error ? err.message : String(err),
        stack: err instanceof Error ? err.stack : 'No stack trace',
        isMobile: /Mobi|Android/i.test(navigator.userAgent),
        online: navigator.onLine
      })
      setLoading(false)
      // Restore previous record if available
      if (previousRecord && previousRecordId) {
        setRecord(previousRecord)
        setRecordId(previousRecordId)
      }
      let errorMsg = err instanceof Error ? err.message : 'Upload failed. Please try again.'
      
      // Add more detailed error info
      if (err instanceof Error && err.message.includes('Network')) {
        errorMsg += ' - Network error, check your WiFi connection'
      } else if (err instanceof Error && err.message.includes('404')) {
        errorMsg += ' - Server not responding (404)'
      } else if (err instanceof Error && err.message.includes('500')) {
        errorMsg += ' - Server error (500)'
      } else if (err instanceof Error && err.message.includes('FormData')) {
        errorMsg += ' - File upload error'
      }
      
      // Add mobile-specific error guidance
      if (/Mobi|Android/i.test(navigator.userAgent)) {
        if (err instanceof Error && err.message.includes('fetch')) {
          errorMsg += ' (Mobile network issue - check WiFi connection)'
        } else if (err instanceof Error && err.message.includes('CORS')) {
          errorMsg += ' (Mobile CORS issue - try refreshing the page)'
        } else if (!navigator.onLine) {
          errorMsg = 'No internet connection - please check your WiFi'
        }
      }
      
      console.error('App: Final error message:', errorMsg)
      setError(errorMsg)
      
      // Ensure error is visible on mobile - use alert as backup if needed
      if (/Mobi|Android/i.test(navigator.userAgent)) {
        // Show error in console, setTimeout ensures it displays even if state update is delayed
        setTimeout(() => {
          console.error('CRITICAL MOBILE ERROR:', errorMsg)
          // Don't use alert() as it can block, but log extensively
          console.error('Mobile Error Details:', {
            type: err instanceof Error ? err.constructor.name : typeof err,
            message: errorMsg,
            online: navigator.onLine,
            userAgent: navigator.userAgent.substring(0, 100)
          })
        }, 100)
      }
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
    console.log('App: handleImageAdd called with files:', newFiles.length)
    console.log('App: Current uploadedImages count:', uploadedImages.length)
    console.log('App: Current record status:', record ? `${record.artist} - ${record.title}` : 'no record')
    console.log('App: Record has database images:', record?.metadata?.image_urls?.length || 0)
    console.log('App: Browser:', navigator.userAgent)
    
    const filesArray = Array.from(newFiles)
    const totalImages = uploadedImages.length + filesArray.length
    
    if (totalImages > 5) {
      alert('Maximum 5 images allowed')
      return
    }
    
    // Update uploaded images state - ALWAYS preserve existing uploaded images
    setUploadedImages(prev => {
      const newImages = [...prev, ...filesArray]
      console.log('App: Updated uploaded images:', prev.length, '→', newImages.length)
      return newImages
    })
    
    // CRITICAL: Always preserve existing record when adding images
    // Whether it's a new record or a record loaded from register
    if (record) {
      console.log('App: Preserving existing record context during image add')
      console.log('App: Record type:', record.status)
      console.log('App: Record source:', record.created_at ? 'database' : 'new')
      
      // Force a small UI update to ensure React re-renders with new image count
      // This prevents browser caching issues
      setRecord(prev => prev ? {
        ...prev,
        updated_at: new Date().toISOString() // Force update timestamp
      } : prev)
      
    } else {
      // If no record yet, start initial analysis
      console.log('App: No existing record, starting initial analysis with:', filesArray.length, 'files')
      handleUpload(filesArray)
    }
  }

  const handleImageRemove = (index: number) => {
    setUploadedImages(prev => prev.filter((_, i) => i !== index))
  }

  const handleReanalyze = async (images: File[]) => {
    console.log('App: Re-analyzing with', images.length, 'uploaded images')
    console.log('App: Current record ID:', recordId)
    console.log('App: Current record has database images:', record?.metadata?.image_urls?.length || 0)
    console.log('App: Browser:', navigator.userAgent)
    
    // Preserve the original record data during re-analysis to prevent context loss
    const originalRecord = record
    const originalRecordId = recordId
    const originalUploadedImages = [...uploadedImages]
    
    if (!recordId || !record) {
      console.log('App: No existing record, using standard upload flow')
      try {
        await handleUpload(images)
      } catch (error) {
        console.error('App: Standard upload failed:', error)
        setError('Analysis failed. Please try again.')
      }
      return
    }
    
    console.log('App: Using enhanced re-analysis endpoint for record:', recordId)
    
    try {
      setError(null)
      setLoading(true)
      
      // Use the new reanalyze endpoint that can handle existing records
      const response = await apiClient.reanalyze(recordId, images)
      console.log('App: Re-analysis started:', response.record_id)
      
      // Start polling for results
      const interval = setInterval(async () => {
        try {
          const statusResponse = await apiClient.getResult(recordId)
          
          if (statusResponse.status === 'complete' || statusResponse.status === 'error') {
            clearInterval(interval)
            setLoading(false)
            setPollInterval(null)
            
            if (statusResponse.status === 'complete') {
              const updatedRecord = statusResponse as unknown as VinylRecord
              setRecord(updatedRecord)
              // Preserve the uploaded images that were used for re-analysis
              setUploadedImages(images)
              console.log('App: Re-analysis completed successfully')
              
              // Update localStorage
              localStorage.setItem('phonox_current_record', JSON.stringify(updatedRecord))
              localStorage.setItem('phonox_current_record_id', recordId)
            } else {
              // Restore previous state on error
              console.error('App: Re-analysis failed, restoring previous state')
              setRecord(originalRecord)
              setRecordId(originalRecordId)
              setUploadedImages(originalUploadedImages)
              setError((statusResponse as any).error || 'Re-analysis failed')
            }
          }
        } catch (err) {
          clearInterval(interval)
          setLoading(false)
          setPollInterval(null)
          // Restore previous state on error
          console.error('App: Re-analysis status check failed:', err)
          setRecord(originalRecord)
          setRecordId(originalRecordId)
          setUploadedImages(originalUploadedImages)
          setError('Failed to get re-analysis status')
        }
      }, POLL_INTERVAL)
      
      setPollInterval(interval)
      
    } catch (error) {
      console.error('App: Re-analysis request failed:', error)
      setLoading(false)
      // Restore previous state on error
      setRecord(originalRecord)
      setRecordId(originalRecordId)
      setUploadedImages(originalUploadedImages)
      setError('Re-analysis failed. Please try again.')
    }
  }

  const handleAddToRegister = async (record: VinylRecord) => {
    // The actual API call is handled in VinylCard component
    // This just triggers a reload of the register
    await loadRegister(currentUser)
  }

  const handleUpdateRegister = async (record: VinylRecord) => {
    // The actual API call is handled in VinylCard component
    // This just triggers a reload of the register
    await loadRegister(currentUser)
  }

  const handleDeleteFromRegister = async (recordId: string) => {
    try {
      await registerApiClient.removeFromRegister(recordId, currentUser)
      await loadRegister(currentUser)
    } catch (error) {
      console.error('Failed to remove from register:', error)
      alert('Failed to remove record from register. Please try again.')
    }
  }

  const handleRecordSelectFromRegister = (registerRecord: RegisterRecord) => {
    console.log('App: Loading record from register:', registerRecord.artist, '-', registerRecord.title)
    console.log('App: Browser:', navigator.userAgent)
    console.log('App: Register record has images:', registerRecord.image_urls?.length || 0)
    
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
      barcode: registerRecord.barcode,
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
        barcode: registerRecord.barcode,
        genres: registerRecord.genres,
        estimated_value_eur: registerRecord.estimated_value_eur,
        image_urls: registerRecord.image_urls || [],
      },
      created_at: registerRecord.created_at,
      updated_at: registerRecord.updated_at,
      user_notes: registerRecord.user_notes,
    }

    // CRITICAL: Set record state first, then clear uploaded images
    console.log('App: Setting register record with', vinylRecord.metadata?.image_urls?.length || 0, 'database images')
    setRecord(vinylRecord)
    setRecordId(registerRecord.id)
    
    // Clear uploaded images since we're loading from register (these are database images)
    console.log('App: Clearing uploaded images for register record (database images will be used)')
    setUploadedImages([])
    
    // Clear localStorage to prevent conflicts
    localStorage.removeItem('phonox_current_record')
    localStorage.removeItem('phonox_current_record_id')
    localStorage.setItem('phonox_register_record_loaded', 'true')
    
    // Browser-specific refresh handling
    const isOpera = navigator.userAgent.indexOf('Opera') !== -1 || navigator.userAgent.indexOf('OPR') !== -1
    const isChrome = navigator.userAgent.indexOf('Chrome') !== -1
    const isSafari = navigator.userAgent.indexOf('Safari') !== -1 && !isChrome
    
    console.log('App: Browser detection - Opera:', isOpera, 'Chrome:', isChrome, 'Safari:', isSafari)
    
    // Opera and Safari need extra state refresh
    if (isOpera || isSafari) {
      console.log('App: Applying browser-specific state refresh for', isOpera ? 'Opera' : 'Safari')
      setTimeout(() => {
        setRecord(prev => prev ? { 
          ...prev, 
          updated_at: new Date().toISOString(),
          // Force UI refresh marker
          _ui_refresh: Math.random()
        } : null)
      }, 100)
    }
    
    // Close the register view
    setShowRegister(false)
    
    console.log('App: Register record loaded successfully')
  }

  const isRecordInRegister = record ? 
    vinylRegister.some(r => r.id === record.record_id) : false

  // Load register from database on component mount
  useEffect(() => {
    if (currentUser) {
      loadRegister(currentUser)
    }
    
    // Try to restore record state from localStorage if available
    const savedRecord = localStorage.getItem('phonox_current_record')
    const savedRecordId = localStorage.getItem('phonox_current_record_id')
    if (savedRecord && savedRecordId && !record) {
      try {
        const parsedRecord = JSON.parse(savedRecord)
        console.log('App: Restored record from localStorage:', parsedRecord.artist, '-', parsedRecord.title)
        setRecord(parsedRecord)
        setRecordId(savedRecordId)
      } catch (error) {
        console.error('App: Failed to restore record from localStorage:', error)
        localStorage.removeItem('phonox_current_record')
        localStorage.removeItem('phonox_current_record_id')
      }
    }
  }, [currentUser])

  // CRITICAL: Persist record state to localStorage when it changes
  // This ensures Opera and other browsers maintain state during image operations
  useEffect(() => {
    if (record && recordId) {
      console.log('App: Persisting record state to localStorage:', record.artist, '-', record.title)
      console.log('App: Browser:', navigator.userAgent.split(' ')[0])
      localStorage.setItem('phonox_current_record', JSON.stringify(record))
      localStorage.setItem('phonox_current_record_id', recordId)
      
      // Opera-specific: Force a DOM refresh marker
      const isOpera = navigator.userAgent.indexOf('Opera') !== -1 || navigator.userAgent.indexOf('OPR') !== -1
      if (isOpera) {
        localStorage.setItem('phonox_opera_state_marker', new Date().toISOString())
      }
    } else if (!record) {
      // Clear localStorage when no record
      localStorage.removeItem('phonox_current_record')
      localStorage.removeItem('phonox_current_record_id')
      localStorage.removeItem('phonox_opera_state_marker')
    }
  }, [record, recordId, uploadedImages.length]) // Include uploadedImages.length to trigger on image changes

  const handleUserChange = (username: string) => {
    console.log('[DEBUG] App: User changed from', currentUser, 'to', username)
    console.log('[DEBUG] App: Mobile detection:', /Mobi|Android/i.test(navigator.userAgent))
    console.log('[DEBUG] App: Navigator online:', navigator.onLine)
    console.log('[DEBUG] App: Window location:', window.location.href)
    
    setCurrentUser(username)
    if (username) {
      console.log('[DEBUG] App: Loading register for new user:', username)
      // Add mobile-specific debug info
      if (/Mobi|Android/i.test(navigator.userAgent)) {
        console.log('[DEBUG] Mobile: About to load register for', username)
        console.log('[DEBUG] Mobile: Current register count before load:', vinylRegister.length)
      }
      loadRegister(username)
    } else {
      console.log('[DEBUG] App: No user, clearing register')
      setVinylRegister([])
    }
  }

  const loadRegister = async (userTag?: string) => {
    const user = userTag || currentUser
    console.log('[DEBUG] App: Loading register for user:', user, 'currentUser:', currentUser, 'userTag:', userTag)
    if (!user) {
      console.log('[DEBUG] App: No user specified, skipping register load')
      return
    }
    setRegisterLoading(true)
    try {
      console.log('[DEBUG] App: Making API call to get register for:', user)
      
      // Enhanced mobile cache control with timestamp-based cache busting
      const isMobile = /Mobi|Android/i.test(navigator.userAgent)
      const cacheHeaders = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
      
      if (isMobile) {
        // Add mobile-specific cache busting
        cacheHeaders['X-Mobile-Cache-Bust'] = Date.now().toString()
        console.log('[DEBUG] App: Mobile detected, using enhanced cache control')
        console.log('[DEBUG] Mobile: API Base URL check...')
      }
      
      console.log('[DEBUG] App: About to call registerApiClient.getRegister')
      const registerData = await registerApiClient.getRegister(user, { 
        cache: 'no-cache',
        headers: cacheHeaders
      })
      
      console.log('[DEBUG] App: Register API call completed successfully')
      console.log('[DEBUG] App: Register loaded, count:', registerData.length)
      console.log('[DEBUG] App: First record sample:', registerData.length > 0 ? registerData[0] : 'No records')
      
      if (isMobile && registerData.length === 0) {
        console.log('[DEBUG] Mobile: No records returned - investigating...')
        console.log('[DEBUG] Mobile: User parameter:', user)
        console.log('[DEBUG] Mobile: Will attempt direct test call')
      }
      
      setVinylRegister(registerData)
      
      if (isMobile) {
        console.log('[DEBUG] Mobile: Register state updated, new count should be:', registerData.length)
      }
    } catch (error) {
      console.error('[DEBUG] Failed to load register:', error)
      console.error('[DEBUG] Error details:', {
        name: error instanceof Error ? error.name : 'Unknown',
        message: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : 'No stack'
      })
      
      if (isMobile) {
        console.error('[DEBUG] Mobile: Register load failed, error was:', error)
      }
    } finally {
      setRegisterLoading(false)
      console.log('[DEBUG] App: Register loading finished, registerLoading set to false')
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
        <div className={styles.headerRight}>
          <UserManager onUserChange={handleUserChange} />
          <button 
            className={styles.registerButton}
            onClick={() => {
              console.log('Register button clicked - currentUser:', currentUser, 'vinylRegister.length:', vinylRegister.length)
              setShowRegister(true)
            }}
            disabled={!currentUser}
            title={!currentUser ? 'Please select a user first' : `${currentUser}'s register with ${vinylRegister.length} records`}
          >
            📚 My Register ({vinylRegister.length}) {!currentUser ? '(No User)' : `(${currentUser})`}
          </button>
        </div>
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
            key={record ? `${record.record_id || record.id}-${uploadedImages.length}-${record.updated_at || ''}` : 'empty'}
            record={record}
            uploadedImages={uploadedImages}
            onMetadataUpdate={handleMetadataUpdate}
            onImageAdd={handleImageAdd}
            onImageRemove={handleImageRemove}
            onAddToRegister={handleAddToRegister}
            onUpdateRegister={handleUpdateRegister}
            onRegisterSuccess={() => loadRegister(currentUser)}
            onReanalyze={handleReanalyze}
            isInRegister={isRecordInRegister}
            currentUser={currentUser}
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