import { useState } from 'react'
import type { ChangeRequest } from '../api'
import { approveChangeRequest, rejectChangeRequest } from '../api'
import { CHANGE_REQUEST_STATUS_STYLE } from '../nodeStyles'

interface Props {
  documentId: string
  changeRequests: ChangeRequest[]
  onDecided: (updated: ChangeRequest) => void
}

const CHANGE_TYPE_LABEL: Record<string, string> = {
  add_task: 'Add step',
  remove_task: 'Remove step',
  modify_task: 'Modify step',
  modify_edge: 'Modify transition',
  unclear: 'Needs clarification',
}

export default function ChangeRequestsPanel({ documentId, changeRequests, onDecided }: Props) {
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function approve(cr: ChangeRequest) {
    setBusy(cr.id)
    setError(null)
    try {
      const updated = await approveChangeRequest(documentId, cr.id)
      onDecided(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to approve change request')
    } finally {
      setBusy(null)
    }
  }

  async function reject(cr: ChangeRequest) {
    setBusy(cr.id)
    setError(null)
    try {
      const updated = await rejectChangeRequest(documentId, cr.id)
      onDecided(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to reject change request')
    } finally {
      setBusy(null)
    }
  }

  if (changeRequests.length === 0) {
    return (
      <div className="px-6 py-6 text-sm text-slate-400" data-testid="change-requests-panel">
        No process-map change requests yet. BPAs can propose changes from the
        chatbot — they&rsquo;ll show up here for review before anything is applied.
      </div>
    )
  }

  return (
    <div className="px-6 py-6" data-testid="change-requests-panel">
      <p className="mb-4 text-xs text-slate-400">
        Changes proposed via the chatbot. Approving creates a new, versioned
        process map — nothing is edited in place.
      </p>
      {error && <p className="mb-3 text-xs text-rose-600">{error}</p>}
      <ul className="space-y-3">
        {changeRequests.map((cr) => {
          const style = CHANGE_REQUEST_STATUS_STYLE[cr.status] ?? CHANGE_REQUEST_STATUS_STYLE.pending
          const isBusy = busy === cr.id
          return (
            <li key={cr.id} className="rounded-xl border border-slate-200 bg-white px-4 py-3.5 shadow-sm" data-testid="change-request-item">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.bg} ${style.accent}`}>
                  {cr.status}
                </span>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-500">
                  {CHANGE_TYPE_LABEL[cr.change_type] ?? cr.change_type}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-700">&ldquo;{cr.request_text}&rdquo;</p>
              {cr.rationale && <p className="mt-1.5 text-xs text-slate-500">{cr.rationale}</p>}
              {cr.decision_notes && (
                <p className="mt-2 rounded-lg bg-slate-50 border border-slate-100 px-3 py-2 text-xs text-slate-500">
                  {cr.decision_notes}
                </p>
              )}
              {cr.status === 'pending' && cr.change_type !== 'unclear' && (
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    disabled={isBusy}
                    onClick={() => approve(cr)}
                    data-testid={`approve-cr-${cr.id}`}
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-40"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={isBusy}
                    onClick={() => reject(cr)}
                    data-testid={`reject-cr-${cr.id}`}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-50 disabled:opacity-40"
                  >
                    Reject
                  </button>
                </div>
              )}
              {cr.status === 'pending' && cr.change_type === 'unclear' && (
                <p className="mt-3 text-[11px] text-amber-600">
                  Couldn&rsquo;t be turned into a structured edit automatically — ask the
                  BPA to rephrase naming the exact step, or reject it.
                </p>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
