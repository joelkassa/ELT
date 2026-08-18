import { useState } from 'react'
import FolderUploadForm from './components/FolderUploadForm'
import DataReview from './components/DataReview'
import SummaryReport from './components/SummaryReport'

export default function App() {
  const [session, setSession] = useState(null)
  const [reviewComplete, setReviewComplete] = useState(false)

  function handleUploaded(result) {
    setReviewComplete(false)
    setSession(result)
  }

  return (
    <div className="app-container">
      <div className="app-header">
        <span className="app-mark">ETL</span>
        <h1>Safe Minds Grant ETL</h1>
      </div>
      <p className="subtitle">
        Select a Year/Grant folder → auto-map into the 8 grant tables → review flagged rows → committed to Postgres → visible in Superset.
      </p>

      <FolderUploadForm onUploaded={handleUploaded} />

      {session && (
        <DataReview
          key={session.sessionId}
          sessionId={session.sessionId}
          preview={session.preview}
          summaryMode={session.summaryMode}
          autoSummary={session.autoSummary}
          onReviewComplete={() => setReviewComplete(true)}
        />
      )}

      {session && reviewComplete && (
        <SummaryReport sessionId={session.sessionId} mode={session.summaryMode} autoLoad={session.autoSummary} />
      )}
    </div>
  )
}