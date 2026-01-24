import { useState, useRef, useEffect } from 'react'
import styles from './ChatPanel.module.css'
import { apiClient } from '../api/client'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

interface ChatPanelProps {
  recordId: string
  currentMetadata?: {
    artist?: string
    title?: string
    year?: number
    label?: string
    catalog_number?: string
    genres?: string[]
  }
  onMetadataUpdate?: (metadata: Record<string, unknown>) => void
  onClose?: () => void
}

export default function ChatPanel({
  recordId,
  currentMetadata,
  onMetadataUpdate,
  onClose,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showMetadataForm, setShowMetadataForm] = useState(false)
  const [metadata, setMetadata] = useState(currentMetadata || {})
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async () => {
    if (!input.trim()) return

    // Add user message to chat
    const userMessage: ChatMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const result = await apiClient.chat(
        recordId,
        input,
        Object.keys(metadata).length > 0 ? metadata : undefined
      )

      // Add assistant message
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: result.message,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, assistantMessage])

      // Update metadata if provided
      if (result.updated_metadata && onMetadataUpdate) {
        setMetadata(result.updated_metadata)
        onMetadataUpdate(result.updated_metadata)
      }
    } catch (error) {
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Failed to process message'}`,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleMetadataChange = (field: string, value: unknown) => {
    setMetadata((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const handleSendMetadata = () => {
    const metadataMessage = `Here are corrections to the metadata: ${JSON.stringify(metadata)}`
    setInput(metadataMessage)
    setShowMetadataForm(false)
  }

  return (
    <div className={styles.chatPanel}>
      <div className={styles.header}>
        <h3>Correct & Refine Record Info</h3>
        {onClose && (
          <button className={styles.closeBtn} onClick={onClose}>
            ✕
          </button>
        )}
      </div>

      <div className={styles.messagesContainer}>
        {messages.length === 0 && (
          <div className={styles.emptyState}>
            <p>👋 Tell me about this vinyl record or use the form below to correct the metadata.</p>
            <p className={styles.subtitle}>
              You can mention pressing year, condition, country, or any other details.
            </p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`${styles.message} ${styles[msg.role]}`}>
            <div className={styles.messageContent}>{msg.content}</div>
            <small className={styles.timestamp}>
              {new Date(msg.timestamp).toLocaleTimeString()}
            </small>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className={styles.metadataFormContainer}>
        {!showMetadataForm ? (
          <button className={styles.toggleBtn} onClick={() => setShowMetadataForm(true)}>
            📝 Edit Metadata Form
          </button>
        ) : (
          <div className={styles.metadataForm}>
            <div className={styles.formGroup}>
              <label>Artist</label>
              <input
                type="text"
                value={(metadata.artist as string) || ''}
                onChange={(e) => handleMetadataChange('artist', e.target.value)}
                placeholder="Artist name"
              />
            </div>

            <div className={styles.formGroup}>
              <label>Title</label>
              <input
                type="text"
                value={(metadata.title as string) || ''}
                onChange={(e) => handleMetadataChange('title', e.target.value)}
                placeholder="Album title"
              />
            </div>

            <div className={styles.formGroup}>
              <label>Year</label>
              <input
                type="number"
                value={(metadata.year as number) || ''}
                onChange={(e) => handleMetadataChange('year', e.target.value ? parseInt(e.target.value) : null)}
                placeholder="Release year"
              />
            </div>

            <div className={styles.formGroup}>
              <label>Label</label>
              <input
                type="text"
                value={(metadata.label as string) || ''}
                onChange={(e) => handleMetadataChange('label', e.target.value)}
                placeholder="Record label"
              />
            </div>

            <div className={styles.formGroup}>
              <label>Catalog Number</label>
              <input
                type="text"
                value={(metadata.catalog_number as string) || ''}
                onChange={(e) => handleMetadataChange('catalog_number', e.target.value)}
                placeholder="e.g., PCS 7088"
              />
            </div>

            <div className={styles.formGroup}>
              <label>Genres</label>
              <input
                type="text"
                value={(metadata.genres as string[])?.join(', ') || ''}
                onChange={(e) =>
                  handleMetadataChange(
                    'genres',
                    e.target.value.split(',').map((g) => g.trim()),
                  )
                }
                placeholder="Rock, Pop (comma separated)"
              />
            </div>

            <div className={styles.formButtons}>
              <button className={styles.submitBtn} onClick={handleSendMetadata}>
                ✓ Send Corrections
              </button>
              <button
                className={styles.cancelBtn}
                onClick={() => setShowMetadataForm(false)}
              >
                ✕ Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      <div className={styles.inputContainer}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSendMessage()
            }
          }}
          placeholder="Type a message... (Shift+Enter for new line)"
          disabled={loading}
          className={styles.input}
        />
        <button
          onClick={handleSendMessage}
          disabled={loading || !input.trim()}
          className={styles.sendBtn}
        >
          {loading ? '⏳' : '→'}
        </button>
      </div>
    </div>
  )
}
