import { useState } from 'react'
import type { Issue, ProcessTask } from '../api'
import { updateIssueFeedback } from '../api'
import { ISSUE_STATUS_LABEL, ISSUE_STATUS_STYLE, ISSUE_TYPE_LABEL, ISSUE_TYPE_STYLE } from '../nodeStyles'

interface Props {
  issues: Issue[]
  tasks: ProcessTask[]
  documentId: string
  onIssueUpdated: (issue: Issue) => void
}

export default function IssuesPanel({ issues, tasks, documentId, onIssueUpdated }: Props) {
  const taskById = new Map(tasks.map((t) => [t.id, t]))
  const [draftFeedback, setDraftFeedback] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function submitFeedback(issueId: string) {
    const text = (draftFeedback[issueId] ?? '').trim()
    if (!text) return
    setBusy(issueId)
    setError(null)
    try {
      const updated = await updateIssueFeedback(documentId, issueId, {
        bpa_feedback: text,
        status: 'pending_review',
      })
      onIssueUpdated(updated)
      setDraftFeedback((d) => ({ ...d, [issueId]: '' }))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to submit feedback')
    } finally {
      setBusy(null)
    }
  }

  async function setStatus(issueId: string, status: 'resolved' | 'deferred' | 'open') {
    setBusy(issueId)
    setError(null)
    try {
      const updated = await updateIssueFeedback(documentId, issueId, { status })
      onIssueUpdated(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update status')
    } finally {
      setBusy(null)
    }
  }

  if (issues.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-slate-400">
        No open gaps or ambiguities logged for this document.
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto px-6 py-6" data-testid="issues-panel">
      <p className="mb-4 text-xs text-slate-400">
        Things the source document doesn&rsquo;t fully resolve. Leave feedback or a
        proposed resolution below, then mark it resolved or deferred once a
        reviewer has confirmed it — this never edits the process map itself.
      </p>
      {error && <p className="mb-3 text-xs text-rose-600">{error}</p>}
      <ul className="space-y-3">
        {issues.map((issue) => {
          const style = ISSUE_TYPE_STYLE[issue.issue_type]
          const statusStyle = ISSUE_STATUS_STYLE[issue.status] ?? ISSUE_STATUS_STYLE.open
          const task = issue.process_task_id ? taskById.get(issue.process_task_id) : null
          const isBusy = busy === issue.id
          return (
            <li key={issue.id} className="rounded-xl border border-slate-200 bg-white px-4 py-3.5 shadow-sm" data-testid="issue-item">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.bg} ${style.accent}`}>
                  {ISSUE_TYPE_LABEL[issue.issue_type]}
                </span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${statusStyle.bg} ${statusStyle.accent}`} data-testid="issue-status">
                  {ISSUE_STATUS_LABEL[issue.status] ?? issue.status}
                </span>
                {task && <span className="text-[11px] text-slate-400">→ {task.title}</span>}
              </div>
              <h3 className="mt-2 text-sm font-medium text-slate-800">{issue.title}</h3>
              <p className="mt-1 text-xs leading-relaxed text-slate-500">{issue.description}</p>
              {issue.claim_refs.length > 0 && (
                <p className="mt-2 text-[11px] text-slate-400">
                  Related citations: {issue.claim_refs.map((c) => `p.${c.page}`).join(', ')}
                </p>
              )}

              {issue.bpa_feedback && (
                <div className="mt-3 rounded-lg bg-blue-50 border border-blue-100 px-3 py-2 text-xs text-blue-900">
                  <span className="font-semibold">BPA feedback: </span>{issue.bpa_feedback}
                </div>
              )}
              {issue.resolution_notes && (
                <div className="mt-2 rounded-lg bg-emerald-50 border border-emerald-100 px-3 py-2 text-xs text-emerald-900">
                  <span className="font-semibold">Resolution: </span>{issue.resolution_notes}
                </div>
              )}

              {issue.status !== 'resolved' && (
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <input
                    value={draftFeedback[issue.id] ?? ''}
                    onChange={(e) => setDraftFeedback((d) => ({ ...d, [issue.id]: e.target.value }))}
                    placeholder="Add feedback or a proposed resolution…"
                    data-testid={`issue-feedback-input-${issue.id}`}
                    className="min-w-[220px] flex-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 placeholder:text-slate-400 focus:border-blue-400 focus:outline-none"
                  />
                  <button
                    type="button"
                    disabled={isBusy || !(draftFeedback[issue.id] ?? '').trim()}
                    onClick={() => submitFeedback(issue.id)}
                    data-testid={`issue-feedback-submit-${issue.id}`}
                    className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-40"
                  >
                    Submit feedback
                  </button>
                  <button
                    type="button"
                    disabled={isBusy}
                    onClick={() => setStatus(issue.id, 'resolved')}
                    data-testid={`issue-resolve-${issue.id}`}
                    className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-40"
                  >
                    Mark resolved
                  </button>
                  <button
                    type="button"
                    disabled={isBusy}
                    onClick={() => setStatus(issue.id, 'deferred')}
                    data-testid={`issue-defer-${issue.id}`}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-100 disabled:opacity-40"
                  >
                    Defer
                  </button>
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
