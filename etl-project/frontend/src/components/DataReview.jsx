import { getTables, submitReview } from '../api'
import { useEffect, useState, useRef } from 'react'

function isClean(row) {
  return (
    (!row.issues || Object.keys(row.issues).length === 0) &&
    Boolean(row.suggested_target_table)
  )
}

function classifyRow(row) {
  const issues = row.issues || {}

  if (!row.suggested_target_table) return 'unmapped'
  if (issues.duplicate) return 'duplicate'
  if (issues.total_row) return 'total_row'

  return 'other'
}

const GROUP_LABELS = {
  unmapped: '⚠ Needs manual table selection',
  duplicate: '⚠ Duplicates (already in database or repeated in this upload)',
  total_row: '⚠ Total / Subtotal rows',
  other: 'Other flagged rows',
}

function RowCard({
  row,
  allTables,
  edits,
  chosenTables,
  onFieldChange,
  onTargetTableChange,
  onAccept,
  onReject,
  removing,
  rowError,
  busy,
}) {
  const issues = row.issues || {}

  const issueEntries = Object.entries(issues).filter(
    ([key]) => key !== 'duplicate' && key !== 'total_row'
  )

  const isDuplicate = Boolean(issues.duplicate)
  const isTotalRow = Boolean(issues.total_row)
  const needsManualTable = !row.suggested_target_table

  const cardClasses = [
    'row-card',
    Object.keys(issues).length > 0 ? 'has-issues' : '',
    isDuplicate ? 'duplicate' : '',
    removing ? 'removing' : '',
  ]
    .filter(Boolean)
    .join(' ')

  /*
   * Get the currently edited value for a field.
   *
   * If the user has edited this field, display the edited value.
   * Otherwise display the original mapped value from the backend.
   */
  function getFieldValue(field, originalValue) {
    if (
      edits[row.staging_id] &&
      Object.prototype.hasOwnProperty.call(edits[row.staging_id], field)
    ) {
      return edits[row.staging_id][field]
    }

    return originalValue ?? ''
  }

  /*
   * The selected target table must come from chosenTables state.
   * The previous code used row._chosenTable, but that property was
   * never updated, so the dropdown appeared to reset.
   */
  const selectedTargetTable =
    chosenTables[row.staging_id] || row.suggested_target_table || ''

  return (
    <div className={cardClasses}>
      <div className="row-meta">
        {row.grant_name ? `${row.grant_name} · ` : ''}
        {row.year ? `${row.year} · ` : ''}
        {row.source_filename} · sheet: {row.sheet_name} · staging #
        {row.staging_id}
        {row.mapping_confidence
          ? ` · mapping confidence ${(row.mapping_confidence * 100).toFixed(0)}%`
          : ''}
      </div>

      {needsManualTable && (
        <div className="field" style={{ marginBottom: 10 }}>
          <label>
            Target table (couldn't auto-detect — please choose)
          </label>

          <select
            value={selectedTargetTable}
            onChange={(e) =>
              onTargetTableChange(row.staging_id, e.target.value)
            }
            disabled={busy}
          >
            <option value="">-- select table --</option>

            {allTables.map((table) => (
              <option key={table} value={table}>
                {table}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="fields-grid">
        {Object.entries(row.mapped_data || {}).map(([field, value]) => {
          /*
           * Display-only helper fields should not be editable.
           */
          if (field.endsWith('_display')) return null

          const currentValue = getFieldValue(field, value)

          return (
            <div className="field" key={field}>
              <label>{field}</label>

              <input
                type="text"
                value={currentValue}
                disabled={busy}
                onChange={(e) =>
                  onFieldChange(
                    row.staging_id,
                    field,
                    e.target.value
                  )
                }
              />
            </div>
          )
        })}
      </div>

      {isTotalRow && (
        <div className="issues-box duplicate-box">
          <strong>Total/Subtotal row</strong>{' '}
          {issues.total_row}
        </div>
      )}

      {issueEntries.length > 0 && (
        <div className="issues-box">
          <strong>Flagged</strong>

          <ul>
            {issueEntries.map(([field, message]) => (
              <li key={field}>
                {field}: {message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {isDuplicate && (
        <div className="issues-box duplicate-box">
          <strong>Duplicate</strong> {issues.duplicate}
        </div>
      )}

      {rowError && (
        <div
          style={{
            color: 'var(--danger)',
            fontSize: 13,
            marginBottom: 8,
          }}
        >
          {rowError}
        </div>
      )}

      <div className="row-actions">
        <button
          className="success"
          disabled={busy}
          onClick={() => onAccept(row)}
        >
          {busy ? 'Saving…' : 'Accept'}
        </button>

        <button
          className="danger"
          disabled={busy}
          onClick={() => onReject(row)}
        >
          Reject
        </button>
      </div>
    </div>
  )
}

export default function DataReview({
  sessionId,
  preview,
  summaryMode,
  autoSummary,
  onReviewComplete,
}) {
  const [flaggedRows, setFlaggedRows] = useState([])
  const [edits, setEdits] = useState({})
  const [chosenTables, setChosenTables] = useState({})
  const [allTables, setAllTables] = useState([])
  const [removingIds, setRemovingIds] = useState(new Set())
  const [busyIds, setBusyIds] = useState(new Set())
  const [bulkBusyGroup, setBulkBusyGroup] = useState(null)
  const [bulkError, setBulkError] = useState(null)
  const [rowErrors, setRowErrors] = useState({})
  const [autoCommitSummary, setAutoCommitSummary] = useState(null)
  const [totalParsed, setTotalParsed] = useState(0)
  const [reviewDone, setReviewDone] = useState(false)

  useEffect(() => {
    getTables()
      .then((data) => setAllTables(data.tables))
      .catch(() => {})
  }, [])

  const autoCommittedRef = useRef(null)

  useEffect(() => {
    if (autoCommittedRef.current === preview) return

    autoCommittedRef.current = preview

    const allRows = Object.values(preview).flat()

    setTotalParsed(allRows.length)
    setReviewDone(false)

    const clean = allRows.filter(isClean)
    const flagged = allRows.filter((row) => !isClean(row))

    setFlaggedRows(flagged)

    if (clean.length > 0) {
      const decisions = clean.map((row) => ({
        staging_id: row.staging_id,
        action: 'accept',
        target_table: row.suggested_target_table,
      }))

      submitReview(decisions)
        .then((res) => {
          setAutoCommitSummary({
            count: clean.length,
            results: res.results,
          })

          if (flagged.length === 0) {
            setReviewDone(true)
          }
        })
        .catch((err) => {
          setAutoCommitSummary({
            count: clean.length,
            error: err.message,
          })
        })
    } else {
      setAutoCommitSummary(null)

      if (flagged.length === 0) {
        setReviewDone(true)
      }
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preview])

  useEffect(() => {
    if (flaggedRows.length === 0 && totalParsed > 0) {
      setReviewDone(true)
    }
  }, [flaggedRows, totalParsed])

  useEffect(() => {
    if (reviewDone && onReviewComplete) {
      onReviewComplete()
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reviewDone])

  /*
   * Store an edited field in the edits state.
   *
   * Example:
   *
   * edits = {
   *   123: {
   *     customer_name: "Ethiopian Blood Bank"
   *   }
   * }
   */
  function handleFieldChange(stagingId, field, value) {
    setEdits((previous) => ({
      ...previous,

      [stagingId]: {
        ...(previous[stagingId] || {}),
        [field]: value,
      },
    }))
  }

  /*
   * Store the user's manually selected target table.
   */
  function handleTargetTableChange(stagingId, table) {
    setChosenTables((previous) => ({
      ...previous,
      [stagingId]: table,
    }))
  }

  function removeRows(stagingIds) {
    const idSet = new Set(stagingIds)

    setRemovingIds(
      (previous) => new Set([...previous, ...stagingIds])
    )

    setTimeout(() => {
      setFlaggedRows((previous) =>
        previous.filter(
          (row) => !idSet.has(row.staging_id)
        )
      )

      setRemovingIds((previous) => {
        const next = new Set(previous)

        stagingIds.forEach((id) => next.delete(id))

        return next
      })
    }, 280)
  }

  /*
   * Accept one row.
   *
   * If the user edited any fields, send action="edit"
   * and include edited_data.
   *
   * Otherwise send action="accept".
   */
  async function handleAccept(row) {
    const stagingId = row.staging_id

    const targetTable =
      chosenTables[stagingId] ||
      row.suggested_target_table

    if (!targetTable) {
      setRowErrors((previous) => ({
        ...previous,
        [stagingId]:
          'Please select a target table before accepting.',
      }))

      return
    }

    setBusyIds(
      (previous) => new Set(previous).add(stagingId)
    )

    setRowErrors((previous) => ({
      ...previous,
      [stagingId]: null,
    }))

    try {
      const rowEdits = edits[stagingId] || {}

      const hasEdits =
        Object.keys(rowEdits).length > 0

      const decision = {
        staging_id: stagingId,

        action: hasEdits
          ? 'edit'
          : 'accept',

        target_table: targetTable,

        edited_data: hasEdits
          ? rowEdits
          : undefined,
      }

      const response = await submitReview([decision])

      const outcome = response.results?.[0]

      if (outcome?.outcome === 'error') {
        setRowErrors((previous) => ({
          ...previous,
          [stagingId]:
            outcome.detail ||
            'Failed to commit row.',
        }))
      } else {
        removeRows([stagingId])

        /*
         * Clean up local edit state after successful submission.
         */
        setEdits((previous) => {
          const next = { ...previous }
          delete next[stagingId]
          return next
        })

        setChosenTables((previous) => {
          const next = { ...previous }
          delete next[stagingId]
          return next
        })
      }
    } catch (err) {
      setRowErrors((previous) => ({
        ...previous,
        [stagingId]:
          err.message ||
          'Failed to submit.',
      }))
    } finally {
      setBusyIds((previous) => {
        const next = new Set(previous)
        next.delete(stagingId)
        return next
      })
    }
  }

  async function handleReject(row) {
    const stagingId = row.staging_id

    setBusyIds(
      (previous) => new Set(previous).add(stagingId)
    )

    setRowErrors((previous) => ({
      ...previous,
      [stagingId]: null,
    }))

    try {
      const response = await submitReview([
        {
          staging_id: stagingId,
          action: 'reject',
        },
      ])

      const outcome = response.results?.[0]

      if (outcome?.outcome === 'error') {
        setRowErrors((previous) => ({
          ...previous,
          [stagingId]:
            outcome.detail ||
            'Failed to reject row.',
        }))
      } else {
        removeRows([stagingId])

        setEdits((previous) => {
          const next = { ...previous }
          delete next[stagingId]
          return next
        })

        setChosenTables((previous) => {
          const next = { ...previous }
          delete next[stagingId]
          return next
        })
      }
    } catch (err) {
      setRowErrors((previous) => ({
        ...previous,
        [stagingId]:
          err.message ||
          'Failed to submit.',
      }))
    } finally {
      setBusyIds((previous) => {
        const next = new Set(previous)
        next.delete(stagingId)
        return next
      })
    }
  }

  async function handleBulkReject(groupKey, rows) {
    setBulkBusyGroup(groupKey)
    setBulkError(null)

    try {
      const decisions = rows.map((row) => ({
        staging_id: row.staging_id,
        action: 'reject',
      }))

      const response = await submitReview(decisions)

      const failedIds = new Set(
        response.results
          .filter((result) => result.outcome === 'error')
          .map((result) => result.staging_id)
      )

      failedIds.forEach((id) => {
        setRowErrors((previous) => ({
          ...previous,
          [id]: 'Failed to reject.',
        }))
      })

      const succeededIds = rows
        .map((row) => row.staging_id)
        .filter((id) => !failedIds.has(id))

      removeRows(succeededIds)

      if (failedIds.size > 0) {
        setBulkError(
          `${failedIds.size} row(s) failed to reject -- see individual row errors below.`
        )
      }
    } catch (err) {
      setBulkError(
        err.message ||
          'Bulk reject failed -- nothing was changed. Try again.'
      )
    } finally {
      setBulkBusyGroup(null)
    }
  }

  async function handleBulkAccept(groupKey, rows) {
    const acceptable = rows.filter(
      (row) =>
        chosenTables[row.staging_id] ||
        row.suggested_target_table
    )

    if (acceptable.length === 0) {
      return
    }

    setBulkBusyGroup(groupKey)
    setBulkError(null)

    try {
      const decisions = acceptable.map((row) => {
        const stagingId = row.staging_id

        const targetTable =
          chosenTables[stagingId] ||
          row.suggested_target_table

        const rowEdits = edits[stagingId] || {}

        const hasEdits =
          Object.keys(rowEdits).length > 0

        return {
          staging_id: stagingId,

          action: hasEdits
            ? 'edit'
            : 'accept',

          target_table: targetTable,

          edited_data: hasEdits
            ? rowEdits
            : undefined,
        }
      })

      const response = await submitReview(decisions)

      const failedIds = new Set(
        response.results
          .filter((result) => result.outcome === 'error')
          .map((result) => result.staging_id)
      )

      failedIds.forEach((id) => {
        setRowErrors((previous) => ({
          ...previous,
          [id]: 'Failed to accept.',
        }))
      })

      const succeededIds = acceptable
        .map((row) => row.staging_id)
        .filter((id) => !failedIds.has(id))

      removeRows(succeededIds)

      /*
       * Remove local edit/table state for successfully committed rows.
       */
      setEdits((previous) => {
        const next = { ...previous }

        succeededIds.forEach((id) => {
          delete next[id]
        })

        return next
      })

      setChosenTables((previous) => {
        const next = { ...previous }

        succeededIds.forEach((id) => {
          delete next[id]
        })

        return next
      })

      if (failedIds.size > 0) {
        setBulkError(
          `${failedIds.size} row(s) failed to accept -- see individual row errors below.`
        )
      }
    } catch (err) {
      setBulkError(
        err.message ||
          'Bulk accept failed -- nothing was changed. Try again.'
      )
    } finally {
      setBulkBusyGroup(null)
    }
  }

  const grouped = {}

  flaggedRows.forEach((row) => {
    const key = classifyRow(row)

    if (!grouped[key]) {
      grouped[key] = []
    }

    grouped[key].push(row)
  })

  const groupOrder = [
    'unmapped',
    'duplicate',
    'total_row',
    'other',
  ]

  const flaggedCount = flaggedRows.length

  return (
    <div className="panel">
      <h2>2. Review</h2>

      <div className="summary-bar">
        <span>
          {totalParsed} rows parsed

          {autoCommitSummary
            ? ` · ${autoCommitSummary.count} clean rows auto-committed`
            : ''}

          {' · '}
          {flaggedCount} flagged for review
        </span>
      </div>

      {bulkError && (
        <div
          style={{
            color: 'var(--danger)',
            marginBottom: 16,
          }}
        >
          {bulkError}
        </div>
      )}

      {flaggedCount === 0 && (
        <p className="empty-state">
          Nothing needs your review right now — clean rows
          were committed automatically.
        </p>
      )}

      {groupOrder.map((groupKey) => {
        const rows = grouped[groupKey]

        if (!rows || rows.length === 0) {
          return null
        }

        const busy = bulkBusyGroup !== null

        return (
          <div
            className="table-group"
            key={groupKey}
          >
            <div className="group-header">
              <h3>
                {GROUP_LABELS[groupKey]} ({rows.length})
              </h3>

              <div className="group-header-actions">
                {groupKey !== 'unmapped' && (
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() =>
                      handleBulkAccept(
                        groupKey,
                        rows
                      )
                    }
                  >
                    {bulkBusyGroup === groupKey
                      ? 'Working…'
                      : `Accept all (${rows.length})`}
                  </button>
                )}

                <button
                  className="danger"
                  disabled={busy}
                  onClick={() =>
                    handleBulkReject(
                      groupKey,
                      rows
                    )
                  }
                >
                  {bulkBusyGroup === groupKey
                    ? 'Working…'
                    : `Reject all (${rows.length})`}
                </button>
              </div>
            </div>

            {rows.map((row) => (
              <RowCard
                key={row.staging_id}
                row={row}
                allTables={allTables}

                /*
                 * These two state objects are now passed
                 * into RowCard so the displayed values stay
                 * synchronized with user edits.
                 */
                edits={edits}
                chosenTables={chosenTables}

                onFieldChange={handleFieldChange}
                onTargetTableChange={
                  handleTargetTableChange
                }
                onAccept={handleAccept}
                onReject={handleReject}

                removing={removingIds.has(
                  row.staging_id
                )}

                busy={busyIds.has(
                  row.staging_id
                )}

                rowError={
                  rowErrors[row.staging_id]
                }
              />
            ))}
          </div>
        )
      })}
    </div>
  )
}