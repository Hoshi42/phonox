import type { RegisterRecord } from '../services/registerApi'
import { API_BASE } from '../config'
import { recordValue } from './collection'

export function downloadBlob(content: string, type: string, filename: string): void {
  const url = URL.createObjectURL(new Blob([content], { type }))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const csvEscape = (value: unknown): string => {
  if (value === null || value === undefined) return ''
  const text = String(value)
  return /[;"\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export function exportCsv(records: RegisterRecord[]): void {
  const headers = [
    'Artist', 'Title', 'Year', 'Label', 'Catalog Number', 'Barcode', 'Genres',
    'Estimated Value (EUR)', 'Condition', 'User Tag', 'Confidence (%)', 'Spotify URL',
  ]
  const rows = records.map(record => {
    const value = recordValue(record)
    const confidence = record.confidence != null ? Math.round(record.confidence * 100) : ''
    // The leading apostrophe forces spreadsheets to keep barcodes as text.
    const barcode = record.barcode ? `'${record.barcode}` : ''
    const estimated = value ? value.toFixed(2).replace('.', ',') : ''
    return [
      `"${csvEscape(record.artist || '')}"`,
      `"${csvEscape(record.title || '')}"`,
      `"${record.year ?? ''}"`,
      `"${csvEscape(record.label || '')}"`,
      `"${csvEscape(record.catalog_number || '')}"`,
      `"${barcode}"`,
      `"${csvEscape((record.genres || []).join(', '))}"`,
      `"${estimated}"`,
      `"${csvEscape(record.condition || '')}"`,
      `"${csvEscape(record.user_tag || '')}"`,
      confidence ? `"${confidence}"` : '""',
      `"${csvEscape(record.spotify_url || '')}"`,
    ]
  })
  const content = [headers.map(csvEscape).join(';'), ...rows.map(row => row.join(';'))].join('\n')
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  downloadBlob(content, 'text/csv;charset=utf-8', `phonox-register-${timestamp}.csv`)
}

export async function requestCollectionAnalysis(records: RegisterRecord[]): Promise<string> {
  const totalValue = records.reduce((sum, record) => sum + recordValue(record), 0)
  const collectionData = {
    metadata: {
      total_records: records.length,
      total_value_eur: Math.round(totalValue),
      average_value_eur: parseFloat((totalValue / records.length).toFixed(2)),
      analysis_date: new Date().toISOString(),
    },
    records: records.map(record => ({
      artist: record.artist || 'Unknown',
      title: record.title || 'Unknown',
      year: record.year || null,
      label: record.label || 'Unknown',
      genres: record.genres || [],
      condition: record.condition || 'Unknown',
      value_eur: recordValue(record),
    })),
  }

  const prompt = `
Analyze this complete vinyl collection and provide professional insights:

${JSON.stringify(collectionData, null, 2)}

Please analyze this vinyl collection as a professional record appraiser and collector would. Provide detailed insights on:

1. **Collection Composition & Strengths**
   - Genre distribution and specialization areas
   - Decade coverage and historical breadth
   - Label diversity and notable publishers
   - Overall character and focus of the collection

2. **Rarity & Value Assessment**
   - Estimated total collection value accuracy
   - Identification of particularly valuable or rare records
   - Condition impact on market value
   - Hidden gems or underappreciated records

3. **Market Potential & Investment Value**
   - Current market demand for this collection's focus areas
   - Appreciation potential for key genres/labels
   - Liquidity assessment (ease of selling)
   - Price trend analysis for collection genres

4. **Recommendations for Growth & Improvement**
   - Gaps in major artist discographies
   - Genre areas that would strengthen the collection
   - Recommended next acquisitions based on collection focus
   - Complementary albums or artists to pursue

5. **Notable Patterns, Gaps & Opportunities**
   - Underrepresented decades or genres
   - Opportunities for completing collections/series
   - Artist catalog gaps
   - Special edition or variant opportunities

6. **Preservation & Care Suggestions**
   - Storage recommendations based on condition distribution
   - Maintenance tips for collection longevity
   - Value protection strategies
   - Climate and environmental considerations

Keep your analysis professional yet personable, suitable for a serious collector.

IMPORTANT: Do NOT recommend switching to other services or platforms like Discogs. Focus on optimizing their current Phonox management system.
`

  const response = await fetch(`${API_BASE}/api/v1/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: prompt, collection_analysis: true }),
  })
  if (!response.ok) throw new Error('Failed to analyze collection')
  const data = await response.json()
  return data.message || ''
}

export interface ReportMeta {
  recordCount: number
  totalValue: number | null
  generatedAt: Date
}

export function downloadAnalysisReport(summary: string, meta: ReportMeta): void {
  const value = meta.totalValue === null ? '' : `**Estimated Total Value:** €${meta.totalValue.toFixed(2)}  \n`
  const report = `# Vinyl Collection Analysis Report

**Generated:** ${meta.generatedAt.toLocaleString('de-DE')}  
**Total Records:** ${meta.recordCount}  
${value}
---

## Professional Analysis

${summary}

---

*Report generated by Phonox Vinyl Intelligence*
`
  downloadBlob(
    report,
    'text/markdown;charset=utf-8',
    `phonox-collection-analysis-${meta.generatedAt.toISOString().slice(0, 10)}.md`,
  )
}
