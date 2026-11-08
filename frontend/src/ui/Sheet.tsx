import { ReactNode, useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import { Icon } from './Icon'
import styles from './Sheet.module.css'

interface SheetProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  /** Optional actions rendered next to the close button. */
  actions?: ReactNode
  /** Larger sheet for content-heavy views such as the record detail. */
  size?: 'default' | 'large'
}

const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'

// Escape and body scroll lock are shared between nested sheets: only the top one reacts.
const stack: symbol[] = []
let lockCount = 0

function lockScroll(): () => void {
  if (lockCount++ === 0) document.body.style.overflow = 'hidden'
  return () => {
    if (--lockCount === 0) document.body.style.overflow = ''
  }
}

/**
 * Bottom sheet on phones, side drawer on wide screens.
 * Handles focus trapping, Escape, scroll locking and drag-to-dismiss on the grab handle.
 */
export function Sheet({ open, title, onClose, children, actions, size = 'default' }: SheetProps) {
  const titleId = useId()
  const panelRef = useRef<HTMLDivElement>(null)
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose
  const dragStart = useRef<number | null>(null)

  useEffect(() => {
    if (!open) return undefined
    const token = Symbol('sheet')
    stack.push(token)
    const unlock = lockScroll()
    const previouslyFocused = document.activeElement as HTMLElement | null
    const panel = panelRef.current
    panel?.focus()

    const onKeyDown = (event: KeyboardEvent) => {
      if (stack[stack.length - 1] !== token) return
      if (event.key === 'Escape') {
        event.stopPropagation()
        onCloseRef.current()
        return
      }
      if (event.key !== 'Tab' || !panel) return
      const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        element => element.offsetParent !== null,
      )
      if (!items.length) {
        event.preventDefault()
        return
      }
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && (document.activeElement === first || document.activeElement === panel)) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)

    return () => {
      document.removeEventListener('keydown', onKeyDown)
      stack.splice(stack.indexOf(token), 1)
      unlock()
      previouslyFocused?.focus?.()
    }
  }, [open])

  if (!open) return null

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    dragStart.current = event.clientY
    event.currentTarget.setPointerCapture(event.pointerId)
  }
  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (dragStart.current === null || !panelRef.current) return
    const delta = Math.max(0, event.clientY - dragStart.current)
    panelRef.current.style.transform = `translateY(${delta}px)`
    panelRef.current.style.transition = 'none'
  }
  const onPointerEnd = (event: React.PointerEvent<HTMLDivElement>) => {
    if (dragStart.current === null || !panelRef.current) return
    const delta = event.clientY - dragStart.current
    dragStart.current = null
    panelRef.current.style.transition = ''
    panelRef.current.style.transform = ''
    if (delta > 110) onClose()
  }

  return createPortal(
    <div className={styles.root}>
      <div className={styles.scrim} onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={`${styles.panel} ${size === 'large' ? styles.large : ''}`}
      >
        <div
          className={styles.grab}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerEnd}
          onPointerCancel={onPointerEnd}
        >
          <span className={styles.handle} />
        </div>
        <header className={styles.header}>
          <h2 id={titleId} className={styles.title}>{title}</h2>
          <div className={styles.actions}>
            {actions}
            <button type="button" className={styles.close} onClick={onClose} aria-label="Close">
              <Icon name="close" size={20} />
            </button>
          </div>
        </header>
        <div className={styles.body}>{children}</div>
      </div>
    </div>,
    document.body,
  )
}
