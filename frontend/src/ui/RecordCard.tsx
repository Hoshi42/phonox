import type { RegisterRecord } from '../services/registerApi'
import { Icon } from './Icon'
import { coverUrl, formatEuro, Layout, recordValue } from '../features/collection'
import styles from './RecordCard.module.css'

interface RecordCardProps {
  record: RegisterRecord
  layout?: Layout
  /** Compact tile used in horizontal shelves. */
  shelf?: boolean
  onOpen: (record: RegisterRecord) => void
}

export function Cover({ src, alt, className }: { src: string | null; alt: string; className?: string }) {
  return (
    <div className={`${styles.cover} ${className || ''}`}>
      {src ? (
        <img src={src} alt={alt} loading="lazy" decoding="async" />
      ) : (
        <span className={styles.placeholder} aria-hidden="true"><Icon name="disc" size={30} /></span>
      )}
    </div>
  )
}

export default function RecordCard({ record, layout = 'grid', shelf = false, onOpen }: RecordCardProps) {
  const title = record.title || 'Unknown title'
  const artist = record.artist || 'Unknown artist'
  const meta = [record.year, formatEuro(recordValue(record))].filter(Boolean).join(' · ')
  const className = [styles.card, layout === 'list' ? styles.list : '', shelf ? styles.shelf : '']
    .filter(Boolean)
    .join(' ')

  return (
    <button
      type="button"
      className={className}
      onClick={() => onOpen(record)}
      aria-label={`${title} by ${artist}`}
    >
      <Cover src={coverUrl(record)} alt="" />
      <span className={styles.text}>
        <span className={styles.title}>{title}</span>
        <span className={styles.artist}>{artist}</span>
        {layout === 'grid' && <span className={styles.meta}>{meta}</span>}
      </span>
      {layout === 'list' && <span className={styles.value}>{formatEuro(recordValue(record))}</span>}
    </button>
  )
}
