import { useEffect, useState } from 'react'
import { getSummary, buildSummaryExportUrl } from '../api'

export default function SummaryReport({ sessionId, mode, autoLoad }) {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [loaded, setLoaded] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const res = await getSummary(sessionId, mode)
      setSummary(res.summary)
      setLoaded(true)
    } catch (err) {
      setError(err.message || 'Failed to load summary.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (autoLoad) load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoLoad, sessionId, mode])

  if (!autoLoad && !loaded) {
    return (
      <div className="panel">
        <h2>3. Summary</h2>
        <p style={{ color: 'var(--muted)' }}>Review is complete. Generate a summary comparing the Excel data against what was committed to the database.</p>
        {error && <div style={{ color: 'var(--danger)', marginBottom: 12 }}>{error}</div>}
        <button onClick={load} disabled={loading}>{loading ? 'Generating…' : 'Generate Summary'}</button>
      </div>
    )
  }

  if (loading && !summary) {
    return <div className="panel"><h2>3. Summary</h2><p className="empty-state">Generating summary…</p></div>
  }

  if (error) {
    return (
      <div className="panel">
        <h2>3. Summary</h2>
        <div style={{ color: 'var(--danger)', marginBottom: 12 }}>{error}</div>
        <button className="secondary" onClick={load}>Retry</button>
      </div>
    )
  }

  if (!summary || summary.length === 0) {
    return <div className="panel"><h2>3. Summary</h2><p className="empty-state">Nothing to summarize yet.</p></div>
  }

  const headers = Object.keys(summary[0])

  return (
    <div className="panel">
      <h2>3. Summary ({mode === 'per_grant' ? 'per grant' : 'combined'})</h2>
      <div className="summary-table-wrap">
        <table className="summary-table">
          <thead>
            <tr>{headers.map((h) => <th key={h}>{h.replace(/_/g, ' ')}</th>)}</tr>
          </thead>
          <tbody>
            {summary.map((row, i) => (
              <tr key={i}>
                {headers.map((h) => {
                  const val = row[h]
                  const isDiff = h.endsWith('_difference')
                  const isNonZeroDiff = isDiff && val !== 0
                  return (
                    <td key={h} className={isNonZeroDiff ? 'diff-nonzero' : ''}>
                      {val === null || val === undefined ? '—' : String(val)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="row-actions">
        <a href={buildSummaryExportUrl(sessionId, 'xlsx', mode)}><button className="secondary">Download Excel</button></a>
        <a href={buildSummaryExportUrl(sessionId, 'csv', mode)}><button className="secondary">Download CSV</button></a>
        <a href={buildSummaryExportUrl(sessionId, 'pdf', mode)}><button className="secondary">Download PDF</button></a>
      </div>
    </div>
  )
}