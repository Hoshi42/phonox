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
  /** When provided, a heart button is shown to toggle the favorite flag. */
  onToggleFavorite?: (record: RegisterRecord) => void
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

export default function RecordCard({ record, layout = 'grid', shelf = false, onOpen, onToggleFavorite }: RecordCardProps) {
  const title = record.title || 'Unknown title'
  const artist = record.artist || 'Unknown artist'
  const meta = [record.year, formatEuro(recordValue(record))].filter(Boolean).join(' · ')
  const favorite = Boolean(record.is_favorite)
  const className = [styles.card, layout === 'list' ? styles.list : '', onToggleFavorite ? styles.withToggle : '']
    .filter(Boolean)
    .join(' ')

  return (
    <div className={`${styles.item} ${shelf ? styles.shelf : ''} ${layout === 'list' ? styles.listItem : ''}`}>
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
      {onToggleFavorite && (
        <button
          type="button"
          className={`${styles.heart} ${favorite ? styles.heartActive : ''}`}
          onClick={() => onToggleFavorite(record)}
          aria-pressed={favorite}
          aria-label={favorite ? `Remove ${title} from favorites` : `Add ${title} to favorites`}
        >
          <Icon name="heart" size={18} fill={favorite ? 'currentColor' : 'none'} />
        </button>
      )}
    </div>
  )
}
