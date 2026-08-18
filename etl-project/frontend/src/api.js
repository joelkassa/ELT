const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export async function getGrants() {
  const res = await fetch(`${API_BASE}/api/grants`)
  if (!res.ok) throw new Error(`Failed to fetch grants: ${res.status}`)
  return res.json()
}

export async function uploadFolderFiles(files, manifest) {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  formData.append('manifest', JSON.stringify(manifest))

  const res = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: formData })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Upload failed: ${res.status} ${text}`)
  }
  return res.json()
}

export async function submitReview(decisions) {
  const res = await fetch(`${API_BASE}/api/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decisions }),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Review submit failed: ${res.status} ${text}`)
  }
  return res.json()
}

export async function getTables() {
  const res = await fetch(`${API_BASE}/api/tables`)
  if (!res.ok) throw new Error(`Failed to fetch tables: ${res.status}`)
  return res.json()
}

export async function getPendingCount(sessionId) {
  const res = await fetch(`${API_BASE}/api/session/${sessionId}/pending-count`)
  if (!res.ok) throw new Error(`Failed to fetch pending count: ${res.status}`)
  return res.json()
}

export async function getSummary(sessionId, mode) {
  const res = await fetch(`${API_BASE}/api/summary/${sessionId}?mode=${mode}`)
  if (!res.ok) throw new Error(`Failed to fetch summary: ${res.status}`)
  return res.json()
}

export function buildSummaryExportUrl(sessionId, format, mode) {
  return `${API_BASE}/api/summary/${sessionId}/export?format=${format}&mode=${mode}`
}