/**
 * ErrorModal Component
 * 
 * Styled error notification modal that matches the app design.
 * Features:
 * - Auto-dismiss after 5 seconds or manual close
 * - Centered overlay with blur background
 * - Gradient styling matching app theme
 * - Error icon and message
 * 
 * @component
 * @param {Object} props - Component props
 * @param {string} props.message - Error message to display
 * @param {Function} props.onClose - Callback when modal closes
 * @param {number} [props.duration] - Auto-close duration in ms (default: 5000)
 * @returns {JSX.Element | null} Error modal or null if not visible
 */

import { useState, useEffect } from 'react'
import styles from './ErrorModal.module.css'

interface ErrorModalProps {
  message: string
  onClose: () => void
  duration?: number
}

export default function ErrorModal({ message, onClose, duration = 5000 }: ErrorModalProps) {
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false)
      onClose()
    }, duration)

    return () => clearTimeout(timer)
  }, [duration, onClose])

  if (!visible) return null

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        <div className={styles.icon}>⚠️</div>
        <h3 className={styles.title}>Error</h3>
        <p className={styles.message}>{message}</p>
        <button
          onClick={() => {
            setVisible(false)
            onClose()
          }}
          className={styles.button}
        >
          Dismiss
        </button>
      </div>
    </div>
  )
}
