import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import styles from './ChatPanel.module.css'

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

export default function ChatPanel({
  record,
  onImageUpload,
  onAnalysisComplete,
  onMetadataUpdate,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: record 
        ? '👋 Hi! Ask me anything about this record - its value, history, pressing details, or collecting tips!'
        : '👋 Hi! I\'m your vinyl expert with web search capabilities. Ask me about vinyl records, prices, market trends, collecting tips, or upload photos for identification!',
      timestamp: new Date().toISOString(),
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

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

    setMessages(prev => [...prev, userMessage])

    // Add system message
    const systemMessage: ChatMessage = {
      role: 'system',
      content: '🔍 Analyzing your vinyl record images... This may take a moment.',
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, systemMessage])
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

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      let response: Response
      
      // Choose endpoint based on whether we have a record
      if (record) {
        // Record-specific chat with integrated web search
        response = await fetch(`/api/v1/identify/${record.record_id}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: userMessage.content })
        })
      } else {
        // General chat with web search capabilities
        response = await fetch('/api/v1/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: userMessage.content })
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
        search_results: data.search_results
      })
      
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: data.message,
        timestamp: new Date().toISOString(),
        webEnhanced: data.web_enhanced,
        sourcesUsed: data.sources_used || 0,
        searchResults: data.search_results || []
      }

      // If we got updated metadata from the chat, notify parent component
      if (data.updated_metadata) {
        console.log('Updated metadata received:', data.updated_metadata)
        onMetadataUpdate?.(data.updated_metadata)
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
      }

      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  // Add analysis result message when record updates
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

**Confidence: ${Math.round(record.confidence * 100)}%**

The vinyl card has been updated with all the details. You can edit any information if needed. Feel free to ask me questions about this record!`,
            timestamp: new Date().toISOString(),
          }
          return [...newMessages, resultMessage]
        })
        setLoading(false)
      }
    }
  }, [record])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleImageUpload(Array.from(e.target.files))
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
            onClick={() => fileInputRef.current?.click()}
            className={styles.uploadBtn}
            title="Upload images"
          >
            📷 Upload
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
                <span className={styles.sender}>System</span>
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
              {message.role === 'assistant' ? (
                <>
                  <div className={styles.markdown} dangerouslySetInnerHTML={{
                    __html: message.content
                      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                      .replace(/\*(.*?)\*/g, '<em>$1</em>')
                      .replace(/\n/g, '<br>')
                      .replace(/^(📅|🏷️|📋|🎵|✅)/gm, '<br>$1')
                  }} />
                  {message.sourcesUsed && message.sourcesUsed > 0 && (
                    <div style={{ 
                      fontSize: '0.75rem', 
                      marginTop: '12px', 
                      padding: '8px',
                      backgroundColor: 'rgba(160, 174, 192, 0.1)',
                      borderRadius: '4px',
                      borderLeft: '3px solid #a0aec0'
                    }}>
                      <div style={{ 
                        fontWeight: 'bold', 
                        marginBottom: '4px',
                        color: '#a0aec0'
                      }}>
                        📄 Sources ({message.sourcesUsed})
                      </div>
                      {(() => {
                        console.log('Rendering sources:', {
                          sourcesUsed: message.sourcesUsed,
                          hasSearchResults: !!message.searchResults,
                          searchResultsLength: message.searchResults?.length || 0,
                          searchResults: message.searchResults
                        })
                        return null
                      })()}
                      {message.searchResults && message.searchResults.length > 0 && (
                        <div style={{ fontSize: '0.7rem' }}>
                          {message.searchResults.map((source, idx) => (
                            <div key={idx} style={{ marginBottom: '4px' }}>
                              <a 
                                href={source.url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                style={{ 
                                  color: '#4299e1',
                                  textDecoration: 'none'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                                onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                              >
                                {idx + 1}. {source.title}
                              </a>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
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
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div style={{ fontSize: '0.8rem', marginTop: '4px', opacity: 0.7 }}>
                {record ? 'Thinking...' : 'Searching the web...'}
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
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              record 
                ? "Ask about this record, its value, history... (use /web to force web search)"
                : "Ask about vinyl records, prices, artists, collecting tips... (use /web to force web search)"
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
          <button 
            onClick={() => fileInputRef.current?.click()}
            className={styles.quickActionBtn}
          >
            📷 Upload Images
          </button>
          {record ? (
            // Record-specific quick actions
            <>
              <button 
                onClick={() => setInput("What's the current market value?")}
                className={styles.quickActionBtn}
              >
                💰 Check Value
              </button>
              <button 
                onClick={() => setInput("/web Tell me about this pressing")}
                className={styles.quickActionBtn}
              >
                🌐 Web Search
              </button>
              <button 
                onClick={() => setInput("What should I know about condition?")}
                className={styles.quickActionBtn}
              >
                🔍 Condition Guide
              </button>
            </>
          ) : (
            // General vinyl quick actions
            <>
              <button 
                onClick={() => setInput("What are the most valuable vinyl records?")}
                className={styles.quickActionBtn}
              >
                💎 Valuable Records
              </button>
              <button 
                onClick={() => setInput("/web How do I start collecting vinyl?")}
                className={styles.quickActionBtn}
              >
                🌐 Web Search
              </button>
              <button 
                onClick={() => setInput("What should I look for when buying vinyl?")}
                className={styles.quickActionBtn}
              >
                🛒 Buying Tips
              </button>
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
}