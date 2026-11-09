import { FormEvent, ReactNode, useEffect, useState } from 'react'
import { registerApiClient } from '../services/registerApi'
import { Icon } from '../ui/Icon'
import { Sheet } from '../ui/Sheet'
import styles from './RecordSheet.module.css'

interface RecordSheetProps {
  open: boolean
  title: string
  user: string
  recordId: string | null
  /** Register actions are only offered for records that are saved in the collection. */
  inRegister: boolean
  spotifyUrl?: string
  onClose: () => void
  onRemove: (recordId: string) => Promise<void> | void
  onMoved: () => void
  onAskChat: () => void
  children: ReactNode
}

function MoveDialog({
  open, user, recordId, onClose, onMoved,
}: { open: boolean; user: string; recordId: string; onClose: () => void; onMoved: () => void }) {
  const [users, setUsers] = useState<string[]>([])
  const [target, setTarget] = useState('')
  const [newName, setNewName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return undefined
    let cancelled = false
    setError('')
    setNewName('')
    registerApiClient.getUsers().then(
      result => {
        if (cancelled) return
        const others = result.filter(name => name !== user)
        setUsers(others)
        setTarget(others[0] || '')
      },
      reason => {
        console.error('[RecordSheet] Could not load users:', reason)
        if (!cancelled) setError('Profiles could not be loaded.')
      },
    )
    return () => { cancelled = true }
  }, [open, user])

  const destination = newName.trim() || target
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!destination) return
    setBusy(true)
    setError('')
    try {
      await registerApiClient.moveRecord(recordId, destination, user)
      onMoved()
    } catch (reason) {
      console.error('[RecordSheet] Move failed:', reason)
      setError(reason instanceof Error ? reason.message : 'Failed to move record')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Sheet open={open} title="Move to another profile" onClose={onClose}>
      <form onSubmit={submit} className={styles.form}>
        {error && <p role="alert" className={styles.error}>{error}</p>}
        {users.length > 0 && (
          <label>
            Existing profile
            <select value={target} onChange={event => { setTarget(event.target.value); setNewName('') }}>
              {users.map(name => <option key={name} value={name}>{name}</option>)}
            </select>
          </label>
        )}
        <label>
          {users.length > 0 ? 'Or create a new profile' : 'New profile name'}
          <input value={newName} maxLength={50} onChange={event => setNewName(event.target.value)} autoComplete="off" />
        </label>
        <button type="submit" className={styles.primary} disabled={busy || !destination}>
          {busy ? 'Moving…' : 'Move record'}
        </button>
      </form>
    </Sheet>
  )
}

export default function RecordSheet({
  open, title, user, recordId, inRegister, spotifyUrl, onClose, onRemove, onMoved, onAskChat, children,
}: RecordSheetProps) {
  const [moving, setMoving] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [removing, setRemoving] = useState(false)

  const actions = (spotifyUrl || (inRegister && recordId)) ? (
    <>
      {spotifyUrl && (
        <a
          className={styles.iconAction}
          href={spotifyUrl}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Open on Spotify"
          title="Open on Spotify"
        >
          <Icon name="headphones" size={20} />
        </a>
      )}
      {inRegister && recordId && (
        <>
          <button type="button" className={styles.iconAction} onClick={() => setMoving(true)} aria-label="Move to another profile" title="Move to another profile">
            <Icon name="move" size={20} />
          </button>
          <button type="button" className={`${styles.iconAction} ${styles.danger}`} onClick={() => setConfirming(true)} aria-label="Remove from collection" title="Remove from collection">
            <Icon name="trash" size={20} />
          </button>
        </>
      )}
    </>
  ) : undefined

  const confirmRemoval = async () => {
    if (!recordId) return
    setRemoving(true)
    try {
      await onRemove(recordId)
      setConfirming(false)
      onClose()
    } finally {
      setRemoving(false)
    }
  }

  return (
    <>
      <Sheet open={open} title={title} size="large" onClose={onClose} actions={actions}>
        <button type="button" className={styles.chatButton} onClick={onAskChat}>
          <Icon name="chat" size={18} /> Ask the assistant about this record
        </button>
        {children}
      </Sheet>
      {recordId && (
        <MoveDialog
          open={moving}
          user={user}
          recordId={recordId}
          onClose={() => setMoving(false)}
          onMoved={() => { setMoving(false); onMoved(); onClose() }}
        />
      )}
      <Sheet open={confirming} title="Remove from collection?" onClose={() => setConfirming(false)}>
        <p className={styles.confirmText}>
          “{title}” will be removed from your collection. This cannot be undone.
        </p>
        <div className={styles.confirmActions}>
          <button type="button" className={styles.secondary} onClick={() => setConfirming(false)}>Cancel</button>
          <button type="button" className={styles.destructive} disabled={removing} onClick={confirmRemoval}>
            {removing ? 'Removing…' : 'Remove'}
          </button>
        </div>
      </Sheet>
    </>
  )
}
