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
  barcode?: string
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
    barcode?: string
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
  
  // DEBUG STATE
  const [debugLogs, setDebugLogs] = useState<string[]>([])
  const [debugVisible, setDebugVisible] = useState(false)

  const addDebugLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString()
    const logMessage = `[${timestamp}] ${message}`
    console.log('[DEBUG]', message)
    setDebugLogs(prev => [...prev.slice(-20), logMessage]) // Keep last 20 logs
  }

  const handleUserChange = async (username: string) => {
    addDebugLog(`🔄 User changed to: "${username}"`)
    setCurrentUser(username)
    if (username) {
      addDebugLog(`📞 Starting loadRegister for user: ${username}`)
      await loadRegister(username)
    } else {
      addDebugLog('🚫 No user, clearing register')
      setVinylRegister([])
    }
  }

  const loadRegister = async (userTag?: string) => {
    const user = userTag || currentUser
    addDebugLog(`📋 loadRegister called - user: "${user}", currentUser: "${currentUser}"`)
    
    if (!user) {
      addDebugLog('❌ No user specified, skipping register load')
      return
    }
    
    setRegisterLoading(true)
    addDebugLog(`⏳ Register loading started for: ${user}`)
    
    try {
      // Enhanced mobile cache control
      const isMobile = /Mobi|Android/i.test(navigator.userAgent)
      addDebugLog(`📱 Mobile detected: ${isMobile}`)
      
      const cacheHeaders = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        ...(isMobile ? { 'X-Mobile-Cache-Bust': Date.now().toString() } : {})
      }
      
      addDebugLog(`🔄 About to call registerApiClient.getRegister("${user}")`)
      addDebugLog(`🌐 API Base: ${window.location.hostname}:8000`)
      
      const registerData = await registerApiClient.getRegister(user, { 
        cache: 'no-cache',
        headers: cacheHeaders
      })
      
      addDebugLog(`✅ API call successful! Records received: ${registerData.length}`)
      
      if (registerData.length > 0) {
        addDebugLog(`📀 First record: ${registerData[0].artist} - ${registerData[0].title}`)
      } else {
        addDebugLog(`⚠️ No records returned for user: ${user}`)
      }
      
      setVinylRegister(registerData)
      addDebugLog(`✅ Register state updated - new count: ${registerData.length}`)
      
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error)
      addDebugLog(`❌ Register load failed: ${errorMsg}`)
      console.error('[DEBUG] Register load error:', error)
    } finally {
      setRegisterLoading(false)
      addDebugLog(`🏁 Register loading finished`)
    }
  }

  const handleUpload = async (files: File[]) => {
    const previousRecord = record
    const previousRecordId = recordId
    
    try {
      addDebugLog(`📤 Starting upload with ${files.length} files`)
      setLoading(true)
      setError(null)

      const response = await apiClient.identify(files)
      const newRecordId = response.record_id
      addDebugLog(`✅ Upload successful, record ID: ${newRecordId}`)
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
              const newRecord = statusResponse as unknown as VinylRecord
              setRecord(newRecord)
              addDebugLog(`✅ Analysis complete: ${newRecord.artist} - ${newRecord.title}`)
              
              // Save to localStorage
              localStorage.setItem('phonox_current_record', JSON.stringify(newRecord))
              localStorage.setItem('phonox_current_record_id', newRecordId)
              localStorage.setItem('phonox_cache_timestamp', Date.now().toString())
              
            } else {
              if (previousRecord && previousRecordId) {
                setRecord(previousRecord)
                setRecordId(previousRecordId)
              }
              const errorMsg = (statusResponse as any).error || 'Analysis failed'
              addDebugLog(`❌ Analysis failed: ${errorMsg}`)
              setError(errorMsg)
            }
          }
        } catch (err) {
          addDebugLog(`❌ Polling error: ${err}`)
          clearInterval(interval)
          setLoading(false)
          setPollInterval(null)
          if (previousRecord && previousRecordId) {
            setRecord(previousRecord)
            setRecordId(previousRecordId)
          }
          setError('Failed to get analysis status')
        }
      }, POLL_INTERVAL)

      setPollInterval(interval)
    } catch (err) {
      addDebugLog(`❌ Upload failed: ${err}`)
      setLoading(false)
      if (previousRecord && previousRecordId) {
        setRecord(previousRecord)
        setRecordId(previousRecordId)
      }
      setError(err instanceof Error ? err.message : 'Upload failed. Please try again.')
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
    addDebugLog(`🖼️ Adding ${newFiles.length} images`)
    const filesArray = Array.from(newFiles)
    const totalImages = uploadedImages.length + filesArray.length
    
    if (totalImages > 5) {
      alert('Maximum 5 images allowed')
      return
    }
    
    setUploadedImages(prev => {
      const newImages = [...prev, ...filesArray]
      addDebugLog(`🖼️ Updated uploaded images: ${prev.length} → ${newImages.length}`)
      return newImages
    })
    
    if (record) {
      addDebugLog('📝 Preserving existing record during image add')
      setRecord(prev => prev ? {
        ...prev,
        updated_at: new Date().toISOString()
      } : prev)
    } else {
      addDebugLog('🚀 No existing record, starting analysis')
      handleUpload(filesArray)
    }
  }

  const handleImageRemove = (index: number) => {
    setUploadedImages(prev => prev.filter((_, i) => i !== index))
  }

  const handleReanalyze = async (images: File[]) => {
    addDebugLog(`🔄 Re-analyzing with ${images.length} images`)
    
    if (!recordId || !record) {
      addDebugLog('🚀 No existing record, using standard upload')
      await handleUpload(images)
      return
    }
    
    try {
      setError(null)
      setLoading(true)
      const response = await apiClient.reanalyze(recordId, images)
      addDebugLog(`✅ Re-analysis started: ${response.record_id}`)
      // Continue with polling logic similar to handleUpload
    } catch (err) {
      addDebugLog(`❌ Re-analysis failed: ${err}`)
      setLoading(false)
      setError(err instanceof Error ? err.message : 'Re-analysis failed')
    }
  }

  return (
    <div className={styles.container}>
      {/* DEBUG PANEL */}
      <div style={{
        position: 'fixed',
        top: 0,
        right: 0,
        width: debugVisible ? '300px' : '60px',
        height: '100vh',
        background: '#000',
        color: '#00ff00',
        fontFamily: 'monospace',
        fontSize: '10px',
        zIndex: 1000,
        overflow: 'hidden',
        transition: 'width 0.3s ease'
      }}>
        <button
          onClick={() => setDebugVisible(!debugVisible)}
          style={{
            position: 'absolute',
            top: '10px',
            right: '10px',
            background: '#333',
            color: '#fff',
            border: 'none',
            padding: '5px 8px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          {debugVisible ? '❌' : '🐛'}
        </button>
        
        {debugVisible && (
          <div style={{ padding: '10px', paddingTop: '40px' }}>
            <h4 style={{ color: '#fff', margin: '0 0 10px 0' }}>🐛 Live Debug</h4>
            <div style={{ 
              maxHeight: 'calc(100vh - 100px)', 
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              fontSize: '9px',
              lineHeight: '1.2'
            }}>
              {debugLogs.map((log, i) => (
                <div key={i} style={{ 
                  marginBottom: '2px',
                  color: log.includes('❌') ? '#ff4444' : 
                         log.includes('✅') ? '#44ff44' : 
                         log.includes('⚠️') ? '#ffaa44' : '#00ff00'
                }}>
                  {log}
                </div>
              ))}
              {debugLogs.length === 0 && (
                <div style={{ color: '#666' }}>Debug logs werden hier angezeigt...</div>
              )}
            </div>
            
            <div style={{ 
              borderTop: '1px solid #333', 
              marginTop: '10px', 
              paddingTop: '10px',
              fontSize: '9px'
            }}>
              <div>User: {currentUser || 'none'}</div>
              <div>Register: {vinylRegister.length} Einträge</div>
              <div>Loading: {registerLoading ? 'ja' : 'nein'}</div>
              <div>Mobile: {/Mobi|Android/i.test(navigator.userAgent) ? 'ja' : 'nein'}</div>
            </div>
          </div>
        )}
      </div>

      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1 className={styles.title}>
            🎵 Phonox DEBUG
          </h1>
          <p className={styles.subtitle}>
            Debug-Version mit Live-Logging
          </p>
        </div>
        <div className={styles.headerRight}>
          <UserManager onUserChange={handleUserChange} />
          <button 
            className={styles.registerButton}
            onClick={() => {
              addDebugLog(`🔍 Register button clicked - User: ${currentUser}, Count: ${vinylRegister.length}`)
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
            loading={loading}
            error={error}
            onUpload={handleUpload}
            onImageAdd={handleImageAdd}
            onImageRemove={handleImageRemove}
            uploadedImages={uploadedImages}
            onMetadataUpdate={handleMetadataUpdate}
            onReanalyze={handleReanalyze}
          />
        </div>

        {record && (
          <div className={styles.resultContainer}>
            <VinylCard 
              record={record}
              onMetadataUpdate={handleMetadataUpdate}
              currentUser={currentUser}
              onRegisterSuccess={() => loadRegister(currentUser)}
            />
          </div>
        )}

        {showRegister && (
          <VinylRegister 
            isOpen={showRegister}
            onClose={() => setShowRegister(false)}
            records={vinylRegister}
            loading={registerLoading}
            userName={currentUser}
          />
        )}
      </main>
    </div>
  )
}

export default App