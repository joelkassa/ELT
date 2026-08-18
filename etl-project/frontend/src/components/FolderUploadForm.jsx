import { useState, useRef } from 'react'
import { getGrants, uploadFolderFiles } from '../api'

const VALID_EXTENSIONS = ['.xlsx', '.xls']

function parseFileTree(fileList) {
  const tree = {}
  const invalidFiles = []

  Array.from(fileList).forEach((file) => {
    const relPath = file.webkitRelativePath || file.name
    const isValidExt = VALID_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext))
    if (!isValidExt) return

    const parts = relPath.split('/')
    if (parts.length < 3) {
      invalidFiles.push({ relPath, reason: 'not inside a Year/GrantName/ folder structure' })
      return
    }
    const filename = parts[parts.length - 1]
    const grantName = parts[parts.length - 2]
    const yearStr = parts[parts.length - 3]
    const year = parseInt(yearStr, 10)

    if (isNaN(year)) {
      invalidFiles.push({ relPath, reason: `folder "${yearStr}" doesn't look like a year` })
      return
    }

    if (!tree[year]) tree[year] = {}
    if (!tree[year][grantName]) tree[year][grantName] = []
    tree[year][grantName].push({ file, relPath, filename, included: true })
  })

  return { tree, invalidFiles }
}

export default function FolderUploadForm({ onUploaded }) {
  const [tree, setTree] = useState(null)
  const [invalidFiles, setInvalidFiles] = useState([])
  const [summaryMode, setSummaryMode] = useState('per_grant')
  const [autoSummary, setAutoSummary] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [confirmingGrants, setConfirmingGrants] = useState(null)
  const inputRef = useRef(null)

  function handleFolderSelect(e) {
    const { tree: newTree, invalidFiles: invalid } = parseFileTree(e.target.files)
    setTree(newTree)
    setInvalidFiles(invalid)
    setError(null)
  }

  function toggleYear(year, included) {
    setTree((prev) => {
      const next = { ...prev }
      next[year] = { ...next[year] }
      Object.keys(next[year]).forEach((grant) => {
        next[year][grant] = next[year][grant].map((f) => ({ ...f, included }))
      })
      return next
    })
  }

  function toggleGrant(year, grant, included) {
    setTree((prev) => {
      const next = { ...prev }
      next[year] = { ...next[year], [grant]: next[year][grant].map((f) => ({ ...f, included })) }
      return next
    })
  }

  function toggleFile(year, grant, index, included) {
    setTree((prev) => {
      const next = { ...prev }
      const files = [...next[year][grant]]
      files[index] = { ...files[index], included }
      next[year] = { ...next[year], [grant]: files }
      return next
    })
  }

  function getIncludedEntries() {
    const entries = []
    if (!tree) return entries
    Object.entries(tree).forEach(([year, grants]) => {
      Object.entries(grants).forEach(([grantName, files]) => {
        files.forEach(({ file, included }) => {
          if (included) entries.push({ file, grantName, year: parseInt(year, 10) })
        })
      })
    })
    return entries
  }

  async function handleContinue() {
    const entries = getIncludedEntries()
    if (entries.length === 0) {
      setError('No files selected -- check at least one file before continuing.')
      return
    }
    setError(null)
    try {
      const { grants: existingGrants } = await getGrants()
      const existingNames = new Set(existingGrants.map((g) => g.name))
      const newGrantNames = [...new Set(entries.map((e) => e.grantName).filter((n) => !existingNames.has(n)))]

      if (newGrantNames.length > 0) {
        setConfirmingGrants(newGrantNames)
      } else {
        await doUpload(entries)
      }
    } catch (err) {
      setError(err.message || 'Failed to check existing grants.')
    }
  }

  async function doUpload(entries) {
    setLoading(true)
    setError(null)
    try {
      const files = entries.map((e) => e.file)
      const manifest = entries.map((e) => ({ filename: e.file.name, grant_name: e.grantName, year: e.year }))
      const result = await uploadFolderFiles(files, manifest)
      if (result.error) {
        setError(result.error)
        return
      }
      onUploaded({ sessionId: result.session_id, preview: result.preview, summaryMode, autoSummary })
    } catch (err) {
      setError(err.message || 'Upload failed.')
    } finally {
      setLoading(false)
      setConfirmingGrants(null)
    }
  }

  const includedCount = getIncludedEntries().length
  const yearKeys = tree ? Object.keys(tree).sort() : []
  const totalFilesFound = yearKeys.reduce(
    (sum, year) => sum + Object.values(tree[year]).reduce((s, files) => s + files.length, 0),
    0
  )

  return (
    <div className="panel">
      <h2>1. Select folder(s)</h2>

      <label className="folder-dropzone" htmlFor="folder-picker-input">
        <span className="folder-dropzone-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" />
            <path d="M12 12v4M10 14h4" />
          </svg>
        </span>
        <span className="folder-dropzone-text">
          <strong>Click to choose a folder</strong>
          <span>Select the parent folder containing your <code>Year/GrantName/file.xlsx</code> structure — it can hold multiple year folders at once.</span>
        </span>
        <input
          id="folder-picker-input"
          ref={inputRef}
          type="file"
          webkitdirectory=""
          directory=""
          mozdirectory=""
          multiple
          onChange={handleFolderSelect}
          className="folder-dropzone-input"
        />
      </label>

      {tree && (
        <div className="folder-selected-chip">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 6 9 17l-5-5" />
          </svg>
          {totalFilesFound} Excel file{totalFilesFound !== 1 ? 's' : ''} found across {yearKeys.length} year{yearKeys.length !== 1 ? 's' : ''}
        </div>
      )}

      {invalidFiles.length > 0 && (
        <div className="issues-box">
          <strong>Skipped {invalidFiles.length} file(s)</strong>
          <ul>
            {invalidFiles.slice(0, 5).map((f, i) => <li key={i}>{f.relPath} -- {f.reason}</li>)}
            {invalidFiles.length > 5 && <li>...and {invalidFiles.length - 5} more</li>}
          </ul>
        </div>
      )}

      {tree && yearKeys.length > 0 && (
        <div className="folder-tree">
          {yearKeys.map((year) => {
            const grants = tree[year]
            const grantKeys = Object.keys(grants).sort()
            const yearAllIncluded = grantKeys.every((g) => grants[g].every((f) => f.included))
            return (
              <div key={year} className="folder-tree-year">
                <label className="folder-tree-year-header">
                  <input type="checkbox" checked={yearAllIncluded} onChange={(e) => toggleYear(year, e.target.checked)} />
                  {year}
                </label>
                <div className="folder-tree-grants">
                  {grantKeys.map((grantName) => {
                    const files = grants[grantName]
                    const grantAllIncluded = files.every((f) => f.included)
                    return (
                      <div key={grantName}>
                        <label className="folder-tree-grant-header">
                          <input type="checkbox" checked={grantAllIncluded} onChange={(e) => toggleGrant(year, grantName, e.target.checked)} />
                          {grantName}
                          <span className="folder-tree-grant-count">({files.length} file{files.length !== 1 ? 's' : ''})</span>
                        </label>
                        <div className="folder-tree-files">
                          {files.map((f, idx) => (
                            <label key={idx} className="folder-tree-file">
                              <input type="checkbox" checked={f.included} onChange={(e) => toggleFile(year, grantName, idx, e.target.checked)} />
                              {f.filename}
                            </label>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {tree && (
        <div className="upload-row">
          <div className="field">
            <label>Summary mode</label>
            <select value={summaryMode} onChange={(e) => setSummaryMode(e.target.value)}>
              <option value="per_grant">Per grant</option>
              <option value="combined">Combined</option>
            </select>
          </div>
          <div className="field">
            <label>Generate summary</label>
            <select value={autoSummary ? 'auto' : 'manual'} onChange={(e) => setAutoSummary(e.target.value === 'auto')}>
              <option value="auto">Automatically, once review is done</option>
              <option value="manual">Manually (I'll click a button)</option>
            </select>
          </div>
        </div>
      )}

      {error && <div style={{ color: 'var(--danger)', margin: '16px 0' }}>{error}</div>}

      {tree && (
        <button onClick={handleContinue} disabled={loading || includedCount === 0} style={{ marginTop: 16 }}>
          {loading ? 'Uploading…' : `Upload ${includedCount} file${includedCount !== 1 ? 's' : ''}`}
        </button>
      )}

      {confirmingGrants && (
        <div className="panel panel-warn" style={{ marginTop: 20 }}>
          <h3 style={{ color: 'var(--warn)' }}>New grants detected</h3>
          <p style={{ marginTop: 0 }}>These grant names aren't in the system yet. Add them and continue?</p>
          <ul style={{ fontFamily: 'var(--font-mono)', fontSize: 13.5 }}>
            {confirmingGrants.map((name) => <li key={name}>{name}</li>)}
          </ul>
          <div className="row-actions">
            <button onClick={() => doUpload(getIncludedEntries())} disabled={loading}>
              {loading ? 'Uploading…' : 'Confirm & Continue'}
            </button>
            <button className="secondary" onClick={() => setConfirmingGrants(null)} disabled={loading}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}