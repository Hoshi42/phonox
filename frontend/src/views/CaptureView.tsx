import type { ReactNode } from 'react'
import { Icon } from '../ui/Icon'
import styles from './CaptureView.module.css'

interface CaptureViewProps {
  /** Title of the record currently loaded, if any. */
  recordTitle?: string
  onOpenRecord: () => void
  children: ReactNode
}

/** Chat and photo capture. The loaded record is reachable through a chip instead of a second panel. */
export default function CaptureView({ recordTitle, onOpenRecord, children }: CaptureViewProps) {
  return (
    <div className={styles.view}>
      <header className={styles.header}>
        <h1>Capture</h1>
        {recordTitle && (
          <button type="button" className={styles.chip} onClick={onOpenRecord}>
            <Icon name="disc" size={16} />
            <span className={styles.chipText}>{recordTitle}</span>
            <Icon name="chevron-right" size={16} />
          </button>
        )}
      </header>
      <div className={styles.chat}>{children}</div>
    </div>
  )
}
