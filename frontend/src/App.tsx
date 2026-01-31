/**
 * Phonox - AI-Powered Vinyl Collection Agent
 * 
 * Main application component that orchestrates:
 * - Image upload and vinyl record identification
 * - Chat panel for AI assistant interactions
 * - Vinyl card display and metadata editing
 * - Personal vinyl register management
 * - User management and collection organization
 * 
 * @component
 * @returns {JSX.Element} The main application interface
 */

import { useEffect, useState, useRef } from 'react'
import styles from './App.module.css'
import VinylSpinner from './components/VinylSpinner'
import ChatPanel, { ChatPanelHandle } from './components/ChatPanel'
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
  condition?: string
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
    estimated_value_usd?: number
    condition?: string
    image_urls?: string[]
  }
  created_at?: string
  updated_at?: string
  user_notes?: string | null
  intermediate_results?: {
    search_query?: string
    search_results_count?: number
    claude_analysis?: string
    search_sources?: Array<{
      title: string
      content: string
    }>
  }
}

function App() {
  const [recordId, setRecordId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const chatPanelRef = useRef<ChatPanelHandle>(null)
  const [record, setRecord] = useState<VinylRecord | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pollInterval, setPollInterval] = useState<any>(null)
  const [uploadedImages, setUploadedImages] = useState<File[]>([])
  const [vinylRegister, setVinylRegister] = useState<RegisterRecord[]>([])
  const [showRegister, setShowRegister] = useState(false)
  const [registerLoading, setRegisterLoading] = useState(false)
  const [currentUser, setCurrentUser] = useState('')
  const [isCheckingValue, setIsCheckingValue] = useState(false)
  const metadataUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null)

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
      const newRecordId = response.record_id as string
      console.log('App: Upload successful, record ID:', newRecordId)
      console.log('App: Initial response keys:', Object.keys(response))
      console.log('App: Initial response status:', response.status)
      console.log('App: Full initial response:', response)
      setRecordId(newRecordId)
      setUploadedImages(files)

      // If already analyzed/complete from initial response, use it
      if (response.status === 'analyzed' || response.status === 'complete') {
        console.log('App: Analysis already complete from initial response, status:', response.status)
        console.log('App: Response has intermediate_results?', !!response.intermediate_results)
        console.log('App: Intermediate results data:', response.intermediate_results)
        const newRecord = response as unknown as VinylRecord
        setRecord(newRecord)
        setLoading(false)
        const timestamp = Date.now()
        localStorage.setItem('phonox_current_record', JSON.stringify(newRecord))
        localStorage.setItem('phonox_current_record_id', newRecordId)
        localStorage.setItem('phonox_cache_timestamp', timestamp.toString())
        return
      }

      console.log('App: Status is', response.status, '- starting polling...')
      
      // Start polling for results
      let pollCount = 0
      const maxPolls = 600 // 10 minutes with 1-second intervals
      const interval = setInterval(async () => {
        pollCount++
        console.log(`App: Poll attempt ${pollCount}/${maxPolls}`)
        try {
          const statusResponse = await apiClient.getResult(newRecordId)
          console.log(`App: Poll ${pollCount} - Status: ${statusResponse.status}`)
          console.log(`App: Poll ${pollCount} - Full response:`, statusResponse)
          
          // Handle different status values - be more flexible
          const status = statusResponse.status || statusResponse.state || 'processing'
          console.log(`App: Poll ${pollCount} - Resolved status to: ${status}`)
          
          if (status === 'analyzed' || status === 'complete' || status === 'failed' || status === 'error') {
            console.log(`App: Poll ${pollCount} - Terminal status detected: ${status}`)
            clearInterval(interval)
            setLoading(false)
            setPollInterval(null)
            console.log('App: Polling finished with status:', status)
            
            if (status === 'analyzed' || status === 'complete') {
              const newRecord = statusResponse as unknown as VinylRecord
              setRecord(newRecord)
              console.log('App: Analysis complete, record set:', newRecord)
              console.log('App: Polling result has intermediate_results?', !!newRecord.intermediate_results)
              console.log('App: Polling result intermediate_results:', newRecord.intermediate_results)
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
            console.error('App: Polling timeout after', pollCount, 'polls')
            clearInterval(interval)
            setLoading(false)
            setPollInterval(null)
            setError('Analysis timeout - please try again')
          }
        } catch (err) {
          console.error('App: Polling error on attempt', pollCount, ':', err)
          console.error('App: Polling error details:', {
            message: err instanceof Error ? err.message : String(err),
            pollCount,
            maxPolls,
            stack: err instanceof Error ? err.stack : 'No stack'
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
            console.error('App: Max polling attempts reached after', pollCount, 'attempts, error:', errorMsg)
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
      // Clear any polling that might be running
      if (pollInterval) {
        clearInterval(pollInterval)
        setPollInterval(null)
      }
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
      // Clear any pending metadata updates to debounce rapid changes (e.g., during typing)
      if (metadataUpdateTimeoutRef.current) {
        clearTimeout(metadataUpdateTimeoutRef.current)
      }
      
      // Debounce metadata updates by 300ms to prevent excessive re-renders during editing
      metadataUpdateTimeoutRef.current = setTimeout(() => {
        setRecord(prev => prev ? {
          ...prev,
          metadata: {
            ...prev.metadata,
            ...metadata
          }
        } : null)
      }, 300)
    }
  }

  const flushMetadataUpdates = () => {
    // Force any pending debounced metadata updates to execute immediately
    if (metadataUpdateTimeoutRef.current) {
      clearTimeout(metadataUpdateTimeoutRef.current)
      metadataUpdateTimeoutRef.current = null
    }
  }

  const handleImageAdd = (newFiles: FileList) => {
    console.log('App: handleImageAdd called with files:', newFiles.length)
    
    const filesArray = Array.from(newFiles)
    const totalImages = uploadedImages.length + filesArray.length
    
    if (totalImages > 5) {
      alert('Maximum 5 images allowed')
      return
    }
    
    // Update uploaded images state
    setUploadedImages(prev => [...prev, ...filesArray])
    
    if (!record) {
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
    console.log('App: Is in register:', isRecordInRegister)
    console.log('App: Current record has database images:', record?.metadata?.image_urls?.length || 0)
    console.log('App: Browser:', navigator.userAgent)
    
    // Preserve the original record data during re-analysis to prevent context loss
    const originalRecord = record
    const originalRecordId = recordId
    const originalUploadedImages = [...uploadedImages]
    
    // If record is NOT in the register (not yet saved to DB), use standard upload flow
    if (!isRecordInRegister || !recordId || !record) {
      console.log('App: Record not in register yet, using standard upload flow')
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
      // Pass current record data so backend doesn't need to query database
      const response = await apiClient.reanalyze(recordId, images, record)
      console.log('App: Re-analysis started:', response.record_id)
      
      // Start polling for results with timeout
      let pollCount = 0
      const maxPolls = 300 // 5 minutes with 1-second intervals
      const interval = setInterval(async () => {
        pollCount++
        try {
          const statusResponse = await apiClient.getResult(recordId)
          
          if (statusResponse.status === 'analyzed' || statusResponse.status === 'complete' || statusResponse.status === 'error') {
            clearInterval(interval)
            setLoading(false)
            setPollInterval(null)
            
            if (statusResponse.status === 'analyzed' || statusResponse.status === 'complete') {
              const updatedRecord = statusResponse as unknown as VinylRecord
              setRecord(updatedRecord)
              // Clear uploaded images since they're now saved to database and included in metadata.image_urls
              setUploadedImages([])
              console.log('App: Re-analysis completed successfully, uploaded images cleared')
              console.log('App: Updated record now has', updatedRecord.metadata?.image_urls?.length || 0, 'images in database')
              
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
          } else if (pollCount > maxPolls) {
            // Timeout after 5 minutes
            clearInterval(interval)
            setLoading(false)
            setPollInterval(null)
            console.error('App: Re-analysis timeout after', pollCount, 'polls')
            setRecord(originalRecord)
            setRecordId(originalRecordId)
            setUploadedImages(originalUploadedImages)
            setError('Re-analysis timeout - took too long. Please try again.')
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
      }, 1000) // Poll every second
      
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
        condition: registerRecord.condition,  // CRITICAL: Include condition in metadata!
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
    
    // Close the register view
    setShowRegister(false)
    
    console.log('App: Register record loaded successfully')
  }

  const handleAnalysisReport = (reportContent: string) => {
    // Add the analysis to chat as a system context message
    if (chatPanelRef.current) {
      chatPanelRef.current.addMessage(reportContent, 'system')
    }
    
    // Close the register modal
    setShowRegister(false)
  }

  const isRecordInRegister = record ? 
    vinylRegister.some(r => r.id === record.record_id) : false

  // Load register from database on component mount
  useEffect(() => {
    if (currentUser) {
      loadRegister(currentUser)
    }
  }, [currentUser])

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (metadataUpdateTimeoutRef.current) {
        clearTimeout(metadataUpdateTimeoutRef.current)
      }
      if (pollInterval) {
        clearInterval(pollInterval)
      }
    }
  }, [])

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
    
    // Enhanced mobile cache control with timestamp-based cache busting
    const isMobile = /Mobi|Android/i.test(navigator.userAgent)
    
    try {
      console.log('[DEBUG] App: Making API call to get register for:', user)
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
        {/* Left: Logo */}
        <div className={styles.headerLeft}>
          <img src="/phonox.png" alt="Phonox" className={styles.logo} />
          <h1 className={styles.title}>Phonox</h1>
        </div>
        
        {/* Right: Register & User */}
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
            📚 My Register ({vinylRegister.length})
          </button>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.chatContainer}>
          <ChatPanel
            ref={chatPanelRef}
            record={record}
            onImageUpload={handleUpload}
            onAnalysisComplete={() => {}}
            onMetadataUpdate={handleMetadataUpdate}
          />
        </div>
        
        <div className={styles.cardContainer}>
          <VinylCard
            key={record?.record_id || 'empty'}
            record={record}
            uploadedImages={uploadedImages}
            onMetadataUpdate={handleMetadataUpdate}
            onImageAdd={handleImageAdd}
            onImageRemove={handleImageRemove}
            onAddToRegister={handleAddToRegister}
            onUpdateRegister={handleUpdateRegister}
            onRegisterSuccess={() => loadRegister(currentUser)}
            onReanalyze={handleReanalyze}
            onAddChatMessage={(content, role) => chatPanelRef.current?.addMessage(content, role)}
            isInRegister={isRecordInRegister}
            currentUser={currentUser}
            isCheckingValue={isCheckingValue}
            onSetIsCheckingValue={setIsCheckingValue}
          />
        </div>
      </main>

      {showRegister && (
        <VinylRegister
          records={vinylRegister}
          onClose={() => setShowRegister(false)}
          onDeleteRecord={handleDeleteFromRegister}
          onRecordSelect={handleRecordSelectFromRegister}
          onAnalysisReport={handleAnalysisReport}
        />
      )}

      {loading && (
        <div className={styles.loadingOverlay}>
          <div className={styles.loadingContent}>
            <VinylSpinner />
          </div>
        </div>
      )}

      {isCheckingValue && (
        <div className={styles.loadingOverlay}>
          <div className={styles.loadingContent}>
            <VinylSpinner 
              message="Estimating Market Value..."
              subtext="Searching web for current prices"
            />
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