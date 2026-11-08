import { useCallback, useEffect, useState } from 'react'

export type ThemePreference = 'system' | 'light' | 'dark'

const STORAGE_KEY = 'phonox_theme'
const META_COLORS = { light: '#f5f4f0', dark: '#0d0d10' }

function readPreference(): ThemePreference {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'light' || stored === 'dark' ? stored : 'system'
  } catch {
    return 'system'
  }
}

function systemTheme(): 'light' | 'dark' {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function apply(preference: ThemePreference): void {
  const root = document.documentElement
  if (preference === 'system') {
    root.removeAttribute('data-theme')
  } else {
    root.setAttribute('data-theme', preference)
  }
  const effective = preference === 'system' ? systemTheme() : preference
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', META_COLORS[effective])
}

/** Applies the stored theme before React renders, so there is no flash on load. */
export function initTheme(): void {
  apply(readPreference())
}

export function useTheme() {
  const [preference, setPreferenceState] = useState<ThemePreference>(readPreference)

  const setPreference = useCallback((next: ThemePreference) => {
    try {
      if (next === 'system') localStorage.removeItem(STORAGE_KEY)
      else localStorage.setItem(STORAGE_KEY, next)
    } catch (error) {
      console.error('[Theme] Could not persist theme preference:', error)
    }
    setPreferenceState(next)
    apply(next)
  }, [])

  useEffect(() => {
    if (preference !== 'system') return undefined
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const listener = () => apply('system')
    query.addEventListener('change', listener)
    return () => query.removeEventListener('change', listener)
  }, [preference])

  return { preference, setPreference }
}
