import { FormEvent, useEffect, useState } from 'react'
import type { RegisterRecord } from '../services/registerApi'
import { registerApiClient } from '../services/registerApi'
import { ThemePreference } from '../theme/useTheme'
import { Icon, IconName } from '../ui/Icon'
import { Sheet } from '../ui/Sheet'
import AnalysisContent from '../ui/AnalysisContent'
import VinylSpinner from '../components/VinylSpinner'
import CollectionMagazine from '../components/CollectionMagazine'
import { downloadAnalysisReport, exportCsv, requestCollectionAnalysis } from '../features/collectionTools'
import styles from './ProfileView.module.css'

const MAX_NAME = 50

interface ProfilePickerProps {
  current: string
  onSelect: (name: string) => void
}

/** Lists existing profiles and lets the user create a new one. */
function ProfilePicker({ current, onSelect }: ProfilePickerProps) {
  const [users, setUsers] = useState<string[]>([])
  const [loadError, setLoadError] = useState('')
  const [name, setName] = useState('')

  useEffect(() => {
    let cancelled = false
    registerApiClient.getUsers().then(
      result => { if (!cancelled) setUsers(result) },
      error => {
        console.error('[Profile] Could not load profiles:', error)
        if (!cancelled) setLoadError('Existing profiles could not be loaded.')
      },
    )
    return () => { cancelled = true }
  }, [])

  const all = [...new Set([...(current ? [current] : []), ...users])].sort((a, b) => a.localeCompare(b))
  const submit = (event: FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()
    if (trimmed) {
      onSelect(trimmed)
      setName('')
    }
  }

  return (
    <div>
      {loadError && <p role="alert" className={styles.error}>{loadError}</p>}
      <ul className={styles.profiles}>
        {all.map(user => (
          <li key={user}>
            <button type="button" className={styles.profile} onClick={() => onSelect(user)} aria-current={user === current}>
              <span className={styles.initial}>{user.slice(0, 1).toUpperCase()}</span>
              <span className={styles.profileName}>{user}</span>
              {user === current && <Icon name="check" size={20} />}
            </button>
          </li>
        ))}
      </ul>
      <form className={styles.newProfile} onSubmit={submit}>
        <label className="visually-hidden" htmlFor="new-profile">New profile name</label>
        <input
          id="new-profile"
          value={name}
          maxLength={MAX_NAME}
          placeholder="New profile name"
          onChange={event => setName(event.target.value)}
          autoComplete="off"
        />
        <button type="submit" className={styles.primary} disabled={!name.trim()}>
          <Icon name="plus" size={18} /> Add
        </button>
      </form>
    </div>
  )
}

/** Full-screen profile selection shown until a profile has been chosen. */
export function ProfileGate({ onSelect }: { onSelect: (name: string) => void }) {
  return (
    <div className={styles.gate}>
      <div className={styles.gateCard}>
        <img src="/phonox.png" alt="" className={styles.gateLogo} />
        <h1>Welcome to Phonox</h1>
        <p>Choose a collection profile or create a new one.</p>
        <ProfilePicker current="" onSelect={onSelect} />
      </div>
    </div>
  )
}

interface ProfileViewProps {
  user: string
  records: RegisterRecord[]
  theme: ThemePreference
  onThemeChange: (theme: ThemePreference) => void
  onSwitchUser: (name: string) => void
  onDiscussInChat: (report: string) => void
}

const THEMES: Array<{ id: ThemePreference; label: string; icon: IconName }> = [
  { id: 'system', label: 'System', icon: 'monitor' },
  { id: 'light', label: 'Light', icon: 'sun' },
  { id: 'dark', label: 'Dark', icon: 'moon' },
]

export default function ProfileView({
  user, records, theme, onThemeChange, onSwitchUser, onDiscussInChat,
}: ProfileViewProps) {
  const [switching, setSwitching] = useState(false)
  const [analysis, setAnalysis] = useState<{ open: boolean; loading: boolean; summary: string; error: string }>({
    open: false, loading: false, summary: '', error: '',
  })

  const analyze = async () => {
    setAnalysis({ open: true, loading: true, summary: '', error: '' })
    try {
      const summary = await requestCollectionAnalysis(records)
      setAnalysis({ open: true, loading: false, summary, error: '' })
    } catch (error) {
      console.error('[Profile] Collection analysis failed:', error)
      setAnalysis({
        open: true, loading: false, summary: '',
        error: error instanceof Error ? error.message : 'Failed to analyze collection',
      })
    }
  }

  const closeAnalysis = () => {
    if (!analysis.loading) setAnalysis(previous => ({ ...previous, open: false }))
  }

  return (
    <div className={styles.view}>
      <div className={styles.scroll}>
        <header className={styles.header}>
          <h1>Profile</h1>
        </header>

        <section className={styles.card} aria-labelledby="profile-user">
          <div className={styles.identity}>
            <span className={styles.initialLarge}>{user.slice(0, 1).toUpperCase()}</span>
            <div>
              <h2 id="profile-user">{user}</h2>
              <p>{records.length} records in this collection</p>
            </div>
          </div>
          <button type="button" className={styles.secondary} onClick={() => setSwitching(true)}>
            <Icon name="swap" size={18} /> Switch or add profile
          </button>
        </section>

        <section className={styles.card} aria-labelledby="profile-appearance">
          <h2 id="profile-appearance" className={styles.sectionTitle}>Appearance</h2>
          <div className={styles.segmented} role="radiogroup" aria-label="Theme">
            {THEMES.map(option => (
              <button
                key={option.id}
                type="button"
                role="radio"
                aria-checked={theme === option.id}
                className={theme === option.id ? styles.segmentActive : ''}
                onClick={() => onThemeChange(option.id)}
              >
                <Icon name={option.icon} size={18} /> {option.label}
              </button>
            ))}
          </div>
        </section>

        <section className={styles.card} aria-labelledby="profile-tools">
          <h2 id="profile-tools" className={styles.sectionTitle}>Collection tools</h2>
          <button type="button" className={styles.tool} onClick={analyze} disabled={!records.length}>
            <Icon name="chart" /> <span><strong>Analyze collection</strong><small>Professional appraisal and growth tips</small></span>
          </button>
          <button type="button" className={styles.tool} onClick={() => exportCsv(records)} disabled={!records.length}>
            <Icon name="download" /> <span><strong>Export CSV</strong><small>All records as a spreadsheet</small></span>
          </button>
        </section>

        <section className={styles.card} aria-labelledby="profile-magazine">
          <h2 id="profile-magazine" className={styles.sectionTitle}>
            <Icon name="book" size={18} /> Collection magazine
          </h2>
          <CollectionMagazine key={user} user={user} records={records.filter(record => record.user_tag === user)} />
        </section>

        <p className={styles.about}>
          <a href="https://phonox-blog.web.app" target="_blank" rel="noopener noreferrer">Phonox blog</a>
        </p>
      </div>

      <Sheet open={switching} title="Profiles" onClose={() => setSwitching(false)}>
        <ProfilePicker
          current={user}
          onSelect={name => { onSwitchUser(name); setSwitching(false) }}
        />
      </Sheet>

      <Sheet
        open={analysis.open}
        title="Collection analysis"
        size="large"
        onClose={closeAnalysis}
        actions={analysis.summary ? (
          <>
            <button type="button" className={styles.smallAction} onClick={() => { onDiscussInChat(analysis.summary); closeAnalysis() }}>
              <Icon name="chat" size={16} /> Chat
            </button>
            <button type="button" className={styles.smallAction} onClick={() => downloadAnalysisReport(analysis.summary, records)}>
              <Icon name="download" size={16} /> Report
            </button>
          </>
        ) : undefined}
      >
        {analysis.loading ? (
          <VinylSpinner message="Analyzing your collection..." subtext="Professional valuation in progress" />
        ) : analysis.error ? (
          <p role="alert" className={styles.error}>{analysis.error}</p>
        ) : (
          <AnalysisContent text={analysis.summary} />
        )}
      </Sheet>
    </div>
  )
}
