import { ReactNode } from 'react'
import styles from './AnalysisContent.module.css'

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={index}>{part.slice(2, -2)}</strong> : part,
  )
}

const isTableRow = (line: string) => line.includes('|')
const isDivider = (line: string) => /^\s*\|?[\s:|-]+\|?\s*$/.test(line) && line.includes('-')
const cells = (line: string) => line.split('|').map(cell => cell.trim()).filter(Boolean)

/** Renders the markdown subset the analysis model returns: headings, lists, tables, bold text. */
export default function AnalysisContent({ text }: { text: string }) {
  const lines = text.split('\n')
  const blocks: ReactNode[] = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index]
    const trimmed = line.trim()

    if (!trimmed || /^(-{3,}|_{3,})$/.test(trimmed)) {
      index++
    } else if (trimmed.startsWith('#')) {
      const level = Math.min(trimmed.match(/^#+/)![0].length, 3)
      const Tag = (level === 1 ? 'h3' : level === 2 ? 'h3' : 'h4') as 'h3' | 'h4'
      blocks.push(<Tag key={index}>{inline(trimmed.replace(/^#+\s*/, ''))}</Tag>)
      index++
    } else if (isTableRow(trimmed)) {
      const rows: string[] = []
      while (index < lines.length && isTableRow(lines[index])) rows.push(lines[index++])
      const [head, ...body] = rows
      const hasHeader = body.length > 0 && isDivider(body[0])
      const dataRows = (hasHeader ? body.slice(1) : rows).filter(row => !isDivider(row))
      blocks.push(
        <div key={index} className={styles.table}>
          <table>
            {hasHeader && <thead><tr>{cells(head).map((cell, i) => <th key={i}>{inline(cell)}</th>)}</tr></thead>}
            <tbody>
              {dataRows.map((row, r) => (
                <tr key={r}>{cells(row).map((cell, c) => <td key={c}>{inline(cell)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>,
      )
    } else if (/^[-•*]\s/.test(trimmed) || /^\d+\.\s/.test(trimmed)) {
      const ordered = /^\d+\.\s/.test(trimmed)
      const pattern = ordered ? /^\s*\d+\.\s/ : /^\s*[-•*]\s/
      const items: string[] = []
      while (index < lines.length && pattern.test(lines[index])) {
        items.push(lines[index++].replace(pattern, ''))
      }
      const List = ordered ? 'ol' : 'ul'
      blocks.push(<List key={index}>{items.map((item, i) => <li key={i}>{inline(item)}</li>)}</List>)
    } else {
      blocks.push(<p key={index}>{inline(trimmed)}</p>)
      index++
    }
  }

  return <div className={styles.content}>{blocks}</div>
}
