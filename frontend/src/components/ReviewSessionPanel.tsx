import { useState } from 'react'
import type { DraftChangeItem, ReviewSession } from '../api'
import { confirmReviewSession, discardReviewSession, updateDraftItem } from '../api'

interface Props {
  documentId: string
  session: ReviewSession
  onSessionChanged: (session: ReviewSession | null) => void
  onApplied: () => void
  onClose: () => void
}

const CHANGE_TYPE_LABEL: Record<string, string> = {
  add_task: 'Add step',
  remove_task: 'Remove step',
  modify_task: 'Modify step',
  modify_edge: 'Modify transition',
  needs_clarification: 'Needs clarification',
}

const STATUS_STYLE: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-500',
  approved: 'bg-emerald-50 text-emerald-700',
  rejected: 'bg-slate-100 text-slate-400',
  needs_clarification: 'bg-amber-50 text-amber-700',
  superseded: 'bg-slate-50 text-slate-300',
  apply_failed: 'bg-rose-50 text-rose-700',
  applied: 'bg-emerald-50 text-emerald-700',
}

function ItemRow({
  item,
  documentId,
  sessionId,
  onUpdated,
}: {
  item: DraftChangeItem
  documentId: string
  sessionId: string
  onUpdated: (item: DraftChangeItem) => void
}) {
  const [editing, setEditing] = useState(false)
  const [taskId, setTaskId] = useState(String(item.proposed_change.task_id ?? ''))
  const [description, setDescription] = useState(String(item.proposed_change.description ?? ''))
  const [busy, setBusy] = useState(false)

  async function setStatus(status: string) {
    setBusy(true)
    try {
      const updated = await updateDraftItem(documentId, sessionId, item.id, { status })
      onUpdated(updated)
    } finally {
      setBusy(false)
    }
  }

  async function saveEdit() {
    setBusy(true)
    try {
      const payload: Record<string, unknown> =
        item.change_type === 'remove_task'
          ? { task_id: taskId }
          : { task_id: taskId, description }
      const updated = await updateDraftItem(documentId, sessionId, item.id, {
        change_type: item.change_type === 'needs_clarification' ? 'modify_task' : item.change_type,
        proposed_change: payload,
      })
      onUpdated(updated)
      setEditing(false)
    } finally {
      setBusy(false)
    }
  }

  const disabled = busy || ['applied', 'superseded'].includes(item.status)

  return (
    <li className="rounded-xl border border-slate-200 bg-white px-4 py-3.5 shadow-sm" data-testid="draft-item">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
          {CHANGE_TYPE_LABEL[item.change_type] ?? item.change_type}
        </span>
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${STATUS_STYLE[item.status] ?? ''}`} data-testid="draft-item-status">
          {item.status.replace('_', ' ')}
        </span>
        {item.human_override && (
          <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-600">human-edited</span>
        )}
      </div>

      {item.rationale && <p className="mt-2 text-sm text-slate-700">{item.rationale}</p>}
      {item.source_message_refs.length > 0 && (
        <p className="mt-1 text-[11px] text-slate-400">From: {item.source_message_refs.join(', ')}</p>
      )}

      {item.change_type === 'needs_clarification' && !editing && (
        <p className="mt-2 text-xs text-amber-600">
          Couldn&rsquo;t confidently turn this into a structured edit — edit it below to specify exactly what should change, or reject it.
        </p>
      )}

      {editing ? (
        <div className="mt-3 space-y-2">
          <input
            value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
            placeholder="Task id this applies to"
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 placeholder:text-slate-400 focus:border-blue-400 focus:outline-none"
          />
          {item.change_type !== 'remove_task' && (
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="New description"
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 placeholder:text-slate-400 focus:border-blue-400 focus:outline-none"
            />
          )}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={saveEdit}
              data-testid={`save-edit-${item.id}`}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-40"
            >
              Save
            </button>
            <button type="button" onClick={() => setEditing(false)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-500">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        !disabled && (
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => setStatus('approved')}
              data-testid={`approve-item-${item.id}`}
              className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-40"
            >
              Approve
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => setStatus('rejected')}
              data-testid={`reject-item-${item.id}`}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-50 disabled:opacity-40"
            >
              Reject
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => setEditing(true)}
              data-testid={`edit-item-${item.id}`}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-50 disabled:opacity-40"
            >
              Edit
            </button>
          </div>
        )
      )}
    </li>
  )
}

export default function ReviewSessionPanel({ documentId, session, onSessionChanged, onApplied, onClose }: Props) {
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const activeItems = session.items.filter((i) => i.status !== 'superseded')
  const approvedCount = activeItems.filter((i) => i.status === 'approved').length

  function handleItemUpdated(updated: DraftChangeItem) {
    onSessionChanged({
      ...session,
      items: session.items.map((i) => (i.id === updated.id ? updated : i)),
    })
  }

  async function handleConfirm() {
    setConfirming(true)
    setError(null)
    try {
      const result = await confirmReviewSession(documentId, session.id)
      if (result.success) {
        onApplied()
        onSessionChanged(null)
        onClose()
      } else {
        setError(result.error ?? 'Could not apply these changes.')
        if (result.failed_item_id) {
          onSessionChanged({
            ...session,
            items: session.items.map((i) => (i.id === result.failed_item_id ? { ...i, status: 'apply_failed' } : i)),
          })
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to confirm changes')
    } finally {
      setConfirming(false)
    }
  }

  async function handleDiscard() {
    await discardReviewSession(documentId, session.id)
    onSessionChanged(null)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-slate-900/30 px-4" data-testid="review-session-panel">
      <div className="max-h-[85vh] w-full max-w-xl overflow-hidden rounded-2xl bg-white shadow-xl flex flex-col">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Review &amp; apply changes</h2>
            <p className="text-xs text-slate-400">
              Consolidated from your conversation. Nothing is applied until you confirm.
            </p>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600" aria-label="Close">
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {error && <p className="mb-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700">{error}</p>}
          {activeItems.length === 0 ? (
            <p className="text-sm text-slate-400">No proposed changes found in this conversation.</p>
          ) : (
            <ul className="space-y-3">
              {activeItems.map((item) => (
                <ItemRow key={item.id} item={item} documentId={documentId} sessionId={session.id} onUpdated={handleItemUpdated} />
              ))}
            </ul>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-slate-100 px-5 py-4">
          <button type="button" onClick={handleDiscard} className="text-xs font-medium text-slate-400 hover:text-slate-600">
            Discard session
          </button>
          <button
            type="button"
            disabled={confirming || approvedCount === 0}
            onClick={handleConfirm}
            data-testid="confirm-review-session"
            className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-40"
          >
            {confirming ? 'Applying…' : `Confirm & apply (${approvedCount})`}
          </button>
        </div>
      </div>
    </div>
  )
}
