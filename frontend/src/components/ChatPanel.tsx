/**
 * ChatPanel Component
 * 
 * AI-powered chat assistant for vinyl record queries and collection management.
 * Features:
 * - Real-time chat with Claude AI
 * - Image upload for record identification
 * - Web search integration (Tavily + DuckDuckGo fallback)
 * - Context-aware responses based on personal record
 * - Quick action buttons for common queries
 * - Web sources attribution and citations
 * - Chat history persistence with 10-message pair limit (20 max messages per record)
 * 
 * @component
 * @param {ChatPanelProps} props - Component props
 * @param {any} [props.record] - Current vinyl record context
 * @param {Function} [props.onImageUpload] - Callback for image uploads
 * @param {Function} [props.onAnalysisComplete] - Callback when analysis completes
 * @param {Function} [props.onMetadataUpdate] - Callback for metadata updates
 * @returns {JSX.Element} Chat interface
 */

import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react'
import ReactMarkdown from 'react-markdown'
import { fetchWithTimeout, TIMEOUT_PRESETS } from '../api/fetchWithTimeout'
import styles from './ChatPanel.module.css'

// Constants for chat history management
const MAX_MESSAGE_PAIRS = 10 // Keep last 10 message pairs (prompt + response)
const MAX_MESSAGES = MAX_MESSAGE_PAIRS * 2 // 20 total messages max
const CHAT_HISTORY_STORAGE_KEY = 'phonox_chat_history'
const GENERAL_CHAT_THREAD_KEY = 'phonox_general_chat_thread_id'

/** Generate or reuse a stable session ID for the general chat thread. */
function getOrCreateSessionId(): string {
  let id = localStorage.getItem(GENERAL_CHAT_THREAD_KEY)
  if (!id) {
    id = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2) + Date.now().toString(36)
    localStorage.setItem(GENERAL_CHAT_THREAD_KEY, id)
  }
  return id
}

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  images?: File[]
  webEnhanced?: boolean
  sourcesUsed?: number
  searchResults?: Array<{
    title: string
    url: string
    content: string
  }>
}

interface ChatPanelProps {
  record?: any
  onImageUpload?: (files: File[]) => void
  onAnalysisComplete?: (result: any) => void
  onMetadataUpdate?: (metadata: any) => void
  chatInputRef?: React.MutableRefObject<HTMLTextAreaElement | null>
}

interface ChatResponse {
  message: string
  web_enhanced?: boolean
  sources_used?: number
  search_results?: Array<{
    title: string
    url: string
    content: string
  }>
}

export interface ChatPanelHandle {
  addMessage: (content: string, role?: 'user' | 'assistant' | 'system') => void
  addAnalysis: (content: string) => void
}

/**
 * Get chat history for a specific record from localStorage
 * @param recordId - The record ID to load history for
 * @returns Array of stored chat messages
 */
const getStoredChatHistory = (recordId?: string): ChatMessage[] => {
  if (!recordId) return []
  try {
    const storageKey = `${CHAT_HISTORY_STORAGE_KEY}_${recordId}`
    const stored = localStorage.getItem(storageKey)
    if (stored) {
      return JSON.parse(stored).filter((msg: ChatMessage) => !msg.images) // Don't restore File objects
    }
  } catch (error) {
    console.error('Error loading chat history from localStorage:', error)
  }
  return []
}

/**
 * Save chat history to localStorage
 * @param recordId - The record ID to save history for
 * @param messages - Messages to save
 */
const saveChatHistory = (recordId: string | undefined, messages: ChatMessage[]): void => {
  if (!recordId) return
  try {
    const storageKey = `${CHAT_HISTORY_STORAGE_KEY}_${recordId}`
    // Don't store File objects in localStorage
    const serializableMessages = messages.map(msg => ({
      ...msg,
      images: undefined
    }))
    localStorage.setItem(storageKey, JSON.stringify(serializableMessages))
  } catch (error) {
    console.error('Error saving chat history to localStorage:', error)
  }
}

/**
 * Enforce message limit by keeping only the last N messages
 * @param messages - Current messages array
 * @param maxMessages - Maximum number of messages to keep
 * @returns Messages array trimmed to max size
 */
const enforceMessageLimit = (messages: ChatMessage[], maxMessages: number): ChatMessage[] => {
  if (messages.length <= maxMessages) return messages
  
  // Keep greeting message + last N messages
  const greeterIndex = messages.findIndex(msg => msg.role === 'assistant' && msg.timestamp === messages[0].timestamp)
  const isFirstMessage = greeterIndex === 0
  
  if (isFirstMessage && messages.length > 1) {
    // Keep first greeting + last (maxMessages - 1) messages
    return [messages[0], ...messages.slice(-(maxMessages - 1))]
  }
  return messages.slice(-maxMessages)
}

const ChatPanel = forwardRef<ChatPanelHandle, ChatPanelProps>(({
  record,
  onImageUpload,
  onAnalysisComplete,
  onMetadataUpdate,
  chatInputRef,
}: ChatPanelProps, ref) => {
  const initialGreeting = record 
    ? '👋 Hi! Ask me anything about this record - its value, history, pressing details, or collecting tips!'
    : '👋 Hi! I\'m your vinyl expert with web search capabilities. Ask me about vinyl records, prices, market trends, collecting tips, or upload photos for identification!'
  
  // Load initial messages from localStorage if available, otherwise use greeting
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const stored = getStoredChatHistory(record?.record_id)
    if (stored.length > 0) {
      console.log(`💾 Loaded chat history for record ${record?.record_id}: ${stored.length} messages`)
      return stored
    }
    return [
      {
        role: 'assistant',
        content: initialGreeting,
        timestamp: new Date().toISOString(),
      }
    ]
  })
  
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const LOADING_STEPS = [
    'Thinking…',
    'Checking knowledge…',
    'Researching…',
    'Crafting response…',
  ]

  // Cycle loading text while waiting
  useEffect(() => {
    if (!loading) { setLoadingStep(0); return }
    const timer = setInterval(() => setLoadingStep(s => (s + 1) % LOADING_STEPS.length), 2000)
    return () => clearInterval(timer)
  }, [loading])

  // Save chat history whenever messages change
  useEffect(() => {
    saveChatHistory(record?.record_id, messages)
  }, [messages, record?.record_id])

  // Switch chat context when record changes
  useEffect(() => {
    if (record?.record_id) {
      const stored = getStoredChatHistory(record.record_id)
      if (stored.length > 0) {
        console.log(`💾 Switched to chat history for record ${record.record_id}: ${stored.length} messages`)
        setMessages(stored)
      } else {
        console.log(`📝 Starting new chat for record ${record.record_id}`)
        setMessages([
          {
            role: 'assistant',
            content: initialGreeting,
            timestamp: new Date().toISOString(),
          }
        ])
      }
    }
  }, [record?.record_id])

  // Expose addMessage method to parent
  useImperativeHandle(ref, () => ({
    addMessage: (content: string, role: 'user' | 'assistant' | 'system' = 'assistant') => {
      const newMessage: ChatMessage = {
        role,
        content,
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => enforceMessageLimit([...prev, newMessage], MAX_MESSAGES))
    },
    addAnalysis: (content: string) => {
      // Insert a user framing message + assistant analysis as a proper pair so the
      // history sent to the model alternates correctly (user→assistant).
      const timestamp = new Date().toISOString()
      const contextMsg: ChatMessage = {
        role: 'user',
        content: '📊 Here is my collection analysis — please help me explore it:',
        timestamp,
      }
      const analysisMsg: ChatMessage = {
        role: 'assistant',
        content,
        timestamp,
      }
      setMessages(prev => {
        const withContext = enforceMessageLimit([...prev, contextMsg], MAX_MESSAGES)
        return enforceMessageLimit([...withContext, analysisMsg], MAX_MESSAGES)
      })
    }
  }))

  const clearChat = () => {
    const greeting: ChatMessage = {
      role: 'assistant',
      content: initialGreeting,
      timestamp: new Date().toISOString(),
    }
    setMessages([greeting])
    if (record?.record_id) {
      localStorage.removeItem(`${CHAT_HISTORY_STORAGE_KEY}_${record.record_id}`)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    // Auto-resize
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleImageUpload = (files: File[]) => {
    if (files.length === 0) return

    // Add user message with images
    const userMessage: ChatMessage = {
      role: 'user',
      content: `Uploaded ${files.length} image${files.length > 1 ? 's' : ''} for analysis`,
      timestamp: new Date().toISOString(),
      images: Array.from(files)
    }

    setMessages(prev => enforceMessageLimit([...prev, userMessage], MAX_MESSAGES))

    // Add system message
    const systemMessage: ChatMessage = {
      role: 'system',
      content: '🔍 Analyzing your vinyl record images... This may take a moment.',
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => enforceMessageLimit([...prev, systemMessage], MAX_MESSAGES))
    setLoading(true)

    // Trigger analysis
    onImageUpload?.(Array.from(files))
  }

  const handleSendMessage = async () => {
    if (!input.trim()) return

    const userMessage: ChatMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => enforceMessageLimit([...prev, userMessage], MAX_MESSAGES))
    setInput('')
    setLoading(true)

    try {
      // Prepare chat history (exclude current message, exclude system messages, exclude images)
      const chatHistoryForContext = messages
        .filter(msg => msg.role !== 'system' && !msg.images)
        .slice(-8) // Send last 8 messages (4 pairs) for context window optimization
        .map(msg => ({
          role: msg.role,
          content: msg.content
        }))

      let response: Response
      
      // Choose endpoint based on whether we have a record
      if (record) {
        // Record-specific chat — server manages memory via thread_id
        response = await fetchWithTimeout(`/api/v1/identify/${record.record_id}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: userMessage.content,
            thread_id: record.record_id,
          }),
          timeout: TIMEOUT_PRESETS.NORMAL
        })
      } else {
        // General chat — server manages memory via session thread_id
        response = await fetchWithTimeout('/api/v1/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: userMessage.content,
            thread_id: getOrCreateSessionId(),
          }),
          timeout: TIMEOUT_PRESETS.NORMAL
        })
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data: ChatResponse = await response.json()
      
      // Debug logging
      console.log('Chat response data:', {
        web_enhanced: data.web_enhanced,
        sources_used: data.sources_used,
        search_results_count: data.search_results?.length || 0,
        search_results: data.search_results,
        history_context_sent: chatHistoryForContext.length
      })
      
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: data.message,
        timestamp: new Date().toISOString(),
        webEnhanced: data.web_enhanced,
        sourcesUsed: data.sources_used || 0,
        searchResults: data.search_results || []
      }

      setMessages(prev => enforceMessageLimit([...prev, assistantMessage], MAX_MESSAGES))
    } catch (error) {
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
      }

      setMessages(prev => enforceMessageLimit([...prev, errorMessage], MAX_MESSAGES))
    } finally {
      setLoading(false)
    }
  }

  // Add analysis result message when record updates with analysis
  useEffect(() => {
    if (record && messages.length > 0) {
      const lastMessage = messages[messages.length - 1]
      if (lastMessage.role === 'system' && lastMessage.content.includes('Analyzing')) {
        // Remove the "analyzing" message and add result
        setMessages(prev => {
          const newMessages = prev.slice(0, -1)
          const resultMessage: ChatMessage = {
            role: 'assistant',
            content: `✅ **Analysis Complete!**

I've identified your record as:

**${record.metadata?.artist || record.artist || 'Unknown Artist'}** - **${record.metadata?.title || record.title || 'Unknown Title'}**

${record.year || record.metadata?.year ? `📅 Released: ${record.year || record.metadata?.year}` : ''}
${record.label || record.metadata?.label ? `🏷️ Label: ${record.label || record.metadata?.label}` : ''}
${record.catalog_number || record.metadata?.catalog_number ? `📋 Catalog #: ${record.catalog_number || record.metadata?.catalog_number}` : ''}
${record.genres?.length || record.metadata?.genres?.length ? `🎵 Genres: ${(record.genres || record.metadata?.genres)?.join(', ')}` : ''}
${record.metadata?.condition ? `💿 Condition: **${record.metadata.condition}**` : ''}

**Confidence: ${Math.round(record.confidence * 100)}%**

The vinyl card has been updated with all the details. You can edit any information if needed. Feel free to ask me questions about this record!`,
            timestamp: new Date().toISOString(),
          }
          return enforceMessageLimit([...newMessages, resultMessage], MAX_MESSAGES)
        })
        setLoading(false)
      }
    }
  }, [record?.status, record?.record_id])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      console.log('ChatPanel: Handling file selection:', e.target.files.length)
      handleImageUpload(Array.from(e.target.files))
      // Reset the input value to allow selecting the same files again (mobile fix)
      e.target.value = ''
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className={styles.chatPanel}>
      {/* Header */}
      <div className={styles.header}>
        <h2>🎵 Vinyl Assistant</h2>
        <div className={styles.headerActions}>
          <button
            onClick={clearChat}
            className={styles.clearBtn}
            title="Clear conversation"
            disabled={loading}
          >
            🗑️
          </button>
          <button 
            onClick={() => fileInputRef.current?.click()}
            className={styles.uploadBtn}
            title="Upload images"
          >
            + Add Record
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className={styles.messages}>
        {messages.map((message, index) => (
          <div key={index} className={`${styles.message} ${styles[message.role]}`}>
            {message.role === 'user' && (
              <div className={styles.messageHeader}>
                <span className={styles.sender}>You</span>
                <span className={styles.timestamp}>
                  {new Date(message.timestamp).toLocaleTimeString([], { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </span>
              </div>
            )}
            {message.role === 'assistant' && (
              <div className={styles.messageHeader}>
                <span className={styles.sender}>
                  🤖 Assistant
                  {message.webEnhanced && (
                    <span style={{ fontSize: '0.7rem', marginLeft: '6px', opacity: 0.8 }}>
                      🌐 web-enhanced
                    </span>
                  )}
                </span>
                <span className={styles.timestamp}>
                  {new Date(message.timestamp).toLocaleTimeString([], { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </span>
              </div>
            )}
            {message.role === 'system' && (
              <div className={styles.messageHeader}>
                <span className={styles.sender}>📊 Collection Context</span>
              </div>
            )}
            
            <div className={styles.messageContent}>
              {message.images && message.images.length > 0 && (
                <div className={styles.messageImages}>
                  {message.images.map((file, imgIndex) => (
                    <img 
                      key={imgIndex}
                      src={URL.createObjectURL(file)} 
                      alt={`Upload ${imgIndex + 1}`}
                      className={styles.messageImage}
                    />
                  ))}
                </div>
              )}
              {(message.role === 'assistant' || message.role === 'system') ? (
                <>
                  <div className={styles.markdown}>
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                  {message.webEnhanced && (
                    <div className={styles.toolBadge}>🔍 Used web search</div>
                  )}
                  {(message.sourcesUsed ?? 0) > 0 && message.searchResults && message.searchResults.length > 0 && (
                    <details className={styles.sources}>
                      <summary>📄 {message.sourcesUsed} source{message.sourcesUsed !== 1 ? 's' : ''}</summary>
                      {message.searchResults.map((source, idx) => (
                        <div key={idx}>
                          <a href={source.url} target="_blank" rel="noopener noreferrer">
                            {idx + 1}. {source.title}
                          </a>
                        </div>
                      ))}
                    </details>
                  )}
                </>
              ) : (
                <span>{message.content}</span>
              )}
            </div>
          </div>
        ))}
        
        {loading && (
          <div className={`${styles.message} ${styles.assistant}`}>
            <div className={styles.messageHeader}>
              <span className={styles.sender}>🤖 Assistant</span>
            </div>
            <div className={styles.messageContent}>
              <div className={styles.loadingDots}>
                <span></span><span></span><span></span>
              </div>
              <div className={styles.loadingStatus}>
                {LOADING_STEPS[loadingStep]}
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className={styles.inputSection}>
        <div className={styles.inputContainer}>
          <textarea
            ref={chatInputRef}
            value={input}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            placeholder={
              record 
                ? "Ask about this record — value, history, pressings, condition…"
                : "Ask about vinyl records, prices, artists, collecting tips…"
            }
            className={styles.input}
            rows={1}
            disabled={loading}
          />
          <button 
            onClick={handleSendMessage} 
            disabled={!input.trim() || loading}
            className={styles.sendBtn}
            title="Send message"
          >
            ➤
          </button>
        </div>
        
        <div className={styles.quickActions}>
          {record ? (
            <>
              <button onClick={() => setInput("What's the current market value of this record?")} className={styles.quickActionBtn}>💰 Market Value</button>
              <button onClick={() => setInput("Is this a first pressing? How can I tell?")} className={styles.quickActionBtn}>🔍 First Pressing?</button>
              <button onClick={() => setInput("What similar records should I look for?")} className={styles.quickActionBtn}>🎵 Similar Records</button>
            </>
          ) : (
            <>
              <button onClick={() => setInput("What makes a vinyl pressing valuable?")} className={styles.quickActionBtn}>💎 What Makes Value?</button>
              <button onClick={() => setInput("How do I grade vinyl condition accurately?")} className={styles.quickActionBtn}>📋 Grading Guide</button>
              <button onClick={() => setInput("What are the most sought-after vinyl genres?")} className={styles.quickActionBtn}>🎶 Sought-After Genres</button>
              <button onClick={() => setInput("Quiz me on my vinyl collection!")} className={`${styles.quickActionBtn} ${styles.quickActionBtnQuiz}`}>🎯 Quiz My Collection</button>
            </>
          )}
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/*"
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />
    </div>
  )
})

ChatPanel.displayName = 'ChatPanel'
export default ChatPanel