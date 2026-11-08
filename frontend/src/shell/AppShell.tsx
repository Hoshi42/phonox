import type { ReactNode } from 'react'
import { Icon, IconName } from '../ui/Icon'
import styles from './AppShell.module.css'

export type Tab = 'collection' | 'capture' | 'discover' | 'profile'

const TABS: Array<{ id: Tab; label: string; icon: IconName }> = [
  { id: 'collection', label: 'Collection', icon: 'library' },
  { id: 'capture', label: 'Capture', icon: 'sparkle' },
  { id: 'discover', label: 'Discover', icon: 'compass' },
  { id: 'profile', label: 'Profile', icon: 'user' },
]

interface AppShellProps {
  active: Tab
  onChange: (tab: Tab) => void
  views: Record<Tab, ReactNode>
}

/**
 * Bottom tab bar on phones, side rail on wide screens. All views stay mounted so
 * chat history, scroll positions and running jobs survive tab changes.
 */
export default function AppShell({ active, onChange, views }: AppShellProps) {
  return (
    <div className={styles.shell}>
      <nav className={styles.nav} aria-label="Main navigation">
        <img src="/phonox.png" alt="Phonox" className={styles.logo} />
        <ul className={styles.list}>
          {TABS.map(tab => (
            <li key={tab.id}>
              <button
                type="button"
                className={`${styles.tab} ${active === tab.id ? styles.active : ''}`}
                aria-current={active === tab.id ? 'page' : undefined}
                onClick={() => onChange(tab.id)}
              >
                <Icon name={tab.icon} size={24} />
                <span>{tab.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <main className={styles.main}>
        {TABS.map(tab => (
          <section
            key={tab.id}
            className={styles.view}
            hidden={active !== tab.id}
            aria-label={tab.label}
          >
            {views[tab.id]}
          </section>
        ))}
      </main>
    </div>
  )
}
