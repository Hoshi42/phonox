import { useEffect, useRef, useState } from 'react'
import { RegisterRecord } from '../services/registerApi'
import {
  defaultMagazineSettings, magazineApi, MagazineDraft, MagazineSettings, MagazineStatus,
} from '../services/magazineApi'
import styles from './CollectionMagazine.module.css'

interface Props {
  user: string
  records: RegisterRecord[]
}

const busyStatuses = new Set(['preparing', 'researching', 'rendering'])

export default function CollectionMagazine({ user, records }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [status, setStatus] = useState<MagazineStatus | null>(null)
  const [settings, setSettings] = useState<MagazineSettings>({ ...defaultMagazineSettings })
  const [draft, setDraft] = useState<MagazineDraft | null>(null)
  const [dirty, setDirty] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const initialized = useRef(false)
  const busy = !!status && busyStatuses.has(status.status)

  useEffect(() => {
    const controller = new AbortController()
    magazineApi.status(user, true, controller.signal).then(result => {
      setStatus(result)
      if (!initialized.current) {
        setSettings({ ...result.settings, consent: false })
        setDraft(result.draft)
        initialized.current = true
      }
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) {
        console.error('[Magazine] Status request failed:', reason)
        setError(reason instanceof Error ? reason.message : 'Could not load the magazine.')
      }
    })
    return () => controller.abort()
  }, [user, records])

  useEffect(() => {
    if (!busy) return undefined
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const result = await magazineApi.status(user, true, controller.signal)
        if (controller.signal.aborted) return
        setStatus(result)
        setError('')
        if (!busyStatuses.has(result.status)) {
          setDraft(result.draft)
          setDirty(false)
          if (result.draft) setSettings({ ...result.draft.settings, consent: false })
        } else {
          timer = setTimeout(poll, 2000)
        }
      } catch (reason) {
        if (!controller.signal.aborted) {
          console.error('[Magazine] Polling failed:', reason)
          setError(reason instanceof Error ? reason.message : 'Could not refresh progress.')
          timer = setTimeout(poll, 5000)
        }
      }
    }
    timer = setTimeout(poll, 1500)
    return () => { controller.abort(); clearTimeout(timer) }
  }, [busy, user])

  const execute = async (action: () => Promise<void>) => {
    setPending(true)
    setError('')
    try {
      await action()
    } catch (reason) {
      console.error('[Magazine] Action failed:', reason)
      setError(reason instanceof Error ? reason.message : 'Magazine action failed.')
    } finally {
      setPending(false)
    }
  }

  const prepare = () => execute(async () => {
    const result = await magazineApi.prepare(user, settings)
    setStatus(result)
    setDraft(null)
    setDirty(false)
  })

  const save = () => execute(async () => {
    if (!draft || !status) return
    const result = await magazineApi.save(user, draft, status.draft_version)
    setStatus(result)
    setDraft(result.draft)
    setSettings({ ...result.settings, consent: false })
    setDirty(false)
  })

  const publish = () => execute(async () => {
    if (!status) return
    setStatus(await magazineApi.publish(user, status.draft_version))
  })

  const editPreface = (text: string) => {
    if (!draft) return
    setDraft({ ...draft, settings: { ...draft.settings, preface: text } })
    setDirty(true)
  }

  const changes = status?.changes
  const hasChanges = !!changes && changes.added + changes.changed + changes.removed > 0
  const unavailable = pending || busy || !status

  return (
    <section className={styles.panel} aria-label="Collection magazine">
      <div className={styles.toolbar}>
        <button onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>
          PDF Magazine {expanded ? '−' : '+'}
        </button>
        <span>One magazine for {user} · A4 · English · EUR</span>
        {status?.has_pdf && (
          <>
            <a href={magazineApi.pdfUrl(user)} target="_blank" rel="noopener noreferrer">Open magazine</a>
            <a href={magazineApi.pdfUrl(user, true)}>Download PDF</a>
          </>
        )}
      </div>
      {expanded && (
        <div className={styles.content}>
          {error && <p role="alert" className={styles.error}>{error}</p>}
          {status?.error && <p role="alert" className={styles.error}>{status.error}</p>}
          {status?.has_pdf && (
            <p>
              Edition {status.edition} · {status.record_count} records · {status.page_count} pages
              {status.published_at && ` · Created ${new Date(status.published_at + (status.published_at.endsWith('Z') ? '' : 'Z')).toLocaleString()}`}
            </p>
          )}
          {status?.has_pdf && hasChanges && (
            <p className={styles.notice}>
              Since the last edition: {changes?.added} new, {changes?.changed} changed,
              {' '}{changes?.removed} removed records. Update to include these changes.
            </p>
          )}
          {busy && (
            <div role="status" aria-live="polite" className={styles.notice}>
              <p>{status?.phase || 'Working on your magazine…'} The existing edition remains available.</p>
              <button disabled={pending} onClick={() => execute(async () => {
                const result = await magazineApi.cancel(user)
                setStatus(result)
                setDraft(result.draft)
              })}>Cancel job</button>
            </div>
          )}
          <details open={!draft && !busy}>
            <summary>{status?.id ? 'Update settings / prepare a new draft' : 'Create your magazine'}</summary>
            <fieldset disabled={unavailable} className={styles.form}>
              <label>Magazine title
                <input value={settings.title} maxLength={200} required
                  onChange={event => setSettings({ ...settings, title: event.target.value })} />
              </label>
              <label>Subtitle
                <input value={settings.subtitle} maxLength={300}
                  onChange={event => setSettings({ ...settings, subtitle: event.target.value })} />
              </label>
              <label>Display name on cover (optional)
                <input value={settings.display_name} maxLength={100}
                  onChange={event => setSettings({ ...settings, display_name: event.target.value })} />
              </label>
              <label>Cover photograph
                <select value={settings.cover_image_id || ''}
                  onChange={event => setSettings({ ...settings, cover_image_id: event.target.value || null })}>
                  <option value="">Typographic cover</option>
                  {records.flatMap(record => record.image_urls.map((url, index) => {
                    const id = url.split('/').pop() || ''
                    return <option key={id} value={id}>{record.artist} / {record.title} / Image {index + 1}</option>
                  }))}
                </select>
              </label>
              <label className={styles.wide}>Foreword (leave empty for a factual proposal)
                <textarea rows={4} value={settings.preface} maxLength={12000}
                  onChange={event => setSettings({ ...settings, preface: event.target.value })} />
              </label>
              <label className={styles.check}>
                <input type="checkbox" checked={settings.include_notes}
                  onChange={event => setSettings({ ...settings, include_notes: event.target.checked })} />
                Include private collector notes in the PDF
              </label>
              <label className={styles.check}>
                <input type="checkbox" checked={settings.research}
                  onChange={event => setSettings({ ...settings, research: event.target.checked, consent: false })} />
                Research artists and albums using available music databases and web sources
              </label>
              <label className={styles.check}>
                <input type="checkbox" checked={settings.refresh_values} disabled={!settings.research}
                  onChange={event => setSettings({ ...settings, refresh_values: event.target.checked })} />
                Research current EUR estimates (existing values otherwise keep their original dates)
              </label>
              {settings.research && (
                <div className={`${styles.notice} ${styles.wide}`}>
                  <p>
                    Planning allowance: approximately EUR {status?.estimated_cost_eur.toFixed(2) || '0.00'}.
                    This is not a provider quote. Hard limit: 20 research/AI steps per job,
                    at most 1,200 output tokens per AI call. MusicBrainz, Discogs and available
                    web search providers are used within this budget. An update can continue unfinished research.
                  </p>
                  <p>Only artist, album and necessary release details go to external providers, never your name or private notes.</p>
                  <label className={styles.check}>
                    <input type="checkbox" checked={settings.consent}
                      onChange={event => setSettings({ ...settings, consent: event.target.checked })} />
                    I approve external research, data transfer and the indicated cost allowance.
                  </label>
                </div>
              )}
              {!records.length && <p className={styles.notice}>The collection is empty. An existing PDF can still be opened.</p>}
              <button className={styles.primary}
                disabled={unavailable || dirty || !records.length || !settings.title.trim() || (settings.research && !settings.consent)}
                onClick={prepare}>
                {status?.id ? 'Update magazine / prepare draft' : 'Prepare magazine'}
              </button>
              {dirty && <p>Save editorial changes before preparing another draft.</p>}
            </fieldset>
          </details>
          {draft && !busy && (
            <section aria-label="Editorial preview">
              <h3>Editorial preview · {draft.records.length} records</h3>
              <p>Review the foreword, artist portraits, groupings and record descriptions before creating the PDF.</p>
              <label>Foreword
                <textarea aria-label="Foreword" rows={7} value={draft.settings.preface} maxLength={12000} disabled={pending}
                  onChange={event => editPreface(event.target.value)} />
              </label>
              {draft.artists.map(artist => (
                <details key={artist.name}>
                  <summary>{artist.name} · Artist portrait</summary>
                  <textarea aria-label={`Portrait: ${artist.name}`} rows={7} maxLength={12000}
                    value={artist.portrait} disabled={pending}
                    onChange={event => {
                      setDraft({ ...draft, artists: draft.artists.map(item => item.name === artist.name
                        ? { ...item, portrait: event.target.value } : item) })
                      setDirty(true)
                    }} />
                  {artist.sources.map(source => (
                    <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer">{source.title}</a>
                  ))}
                </details>
              ))}
              <h4>Record articles</h4>
                  {draft.records.map(record => (
                    <details key={record.id} className={styles.record}>
                      <summary>{record.title || 'Untitled record'} · {record.year || 'Year unknown'}</summary>
                      <div className={styles.images}>
                        {record.images.filter(image => image.width > 0).map(image => (
                          <img key={image.id} src={magazineApi.imageUrl(user, image.id)}
                            alt={`${record.title || 'Record'} / ${image.filename}`} loading="lazy" />
                        ))}
                      </div>
                      <label>Artist chapter (save to refresh the chapter structure)
                        <input value={record.group} maxLength={255} disabled={pending}
                          onChange={event => {
                            setDraft({ ...draft, records: draft.records.map(item => item.id === record.id
                              ? { ...item, group: event.target.value } : item) })
                            setDirty(true)
                          }} />
                      </label>
                      <label>Description
                        <textarea rows={5} maxLength={12000} value={record.description} disabled={pending}
                          onChange={event => {
                            setDraft({ ...draft, records: draft.records.map(item => item.id === record.id
                              ? { ...item, description: event.target.value } : item) })
                            setDirty(true)
                          }} />
                      </label>
                      <p>{record.value_eur === null ? 'Value unavailable'
                        : `${record.value_kind === 'researched' ? 'Research-based' : 'Stored'} estimate: EUR ${record.value_eur.toFixed(2)}`}
                        {' '}· Valuation date: {record.valued_at?.slice(0, 10) || 'unknown'}</p>
                      <p>{record.valuation_note}</p>
                      {record.sources.map(source => (
                        <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer">{source.title}</a>
                      ))}
                </details>
              ))}
              {!!draft.warnings.length && (
                <details><summary>Data and research notes ({draft.warnings.length})</summary>
                  <ul>{draft.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>
                </details>
              )}
              <div className={styles.actions}>
                <button disabled={pending || !dirty || !draft.settings.preface.trim()
                  || draft.records.some(record => !record.group.trim())}
                  onClick={save}>Save editorial changes</button>
                <button className={styles.primary} disabled={pending || dirty} onClick={publish}>
                  Approve &amp; create PDF
                </button>
              </div>
              {dirty && <p role="status">Save your edits and review the refreshed chapters before publication.</p>}
            </section>
          )}
          {!draft && !!status?.warnings?.length && (
            <details><summary>Edition quality notes ({status.warnings.length})</summary>
              <ul>{status.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>
            </details>
          )}
          {status?.id && (
            <button disabled={unavailable} className={styles.delete} onClick={() => {
              if (window.confirm('Delete this magazine and its saved PDF? Your collection will not be changed.')) {
                execute(async () => {
                  await magazineApi.remove(user)
                  const result = await magazineApi.status(user)
                  setStatus(result)
                  setDraft(null)
                  setSettings({ ...defaultMagazineSettings })
                  setDirty(false)
                })
              }
            }}>Delete magazine</button>
          )}
        </div>
      )}
    </section>
  )
}
