import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  getAgenticWorkflow,
  getProcessMap,
  listChangeRequests,
  listDocuments,
  listIssues,
  listProcessMapVersions,
  listValidationCases,
  type AgenticWorkflow,
  type ChangeRequest,
  type DocumentSummary,
  type Issue,
  type ProcessMap,
  type ProcessMapVersionSummary,
  type ValidationCase,
} from './api'
import ProcessMapView from './components/ProcessMapView'
import TaskDetailPanel from './components/TaskDetailPanel'
import IssuesPanel from './components/IssuesPanel'
import ChangeRequestsPanel from './components/ChangeRequestsPanel'
import ChatPanel from './components/ChatPanel'
import ValidationPanel from './components/ValidationPanel'
import AgenticWorkflowPanel from './components/AgenticWorkflowPanel'

type Tab = 'map' | 'feedback' | 'validation' | 'workflow' | 'chat'

export default function App() {
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null)
  const [processMap, setProcessMap] = useState<ProcessMap | null>(null)
  const [issues, setIssues] = useState<Issue[]>([])
  const [changeRequests, setChangeRequests] = useState<ChangeRequest[]>([])
  const [versions, setVersions] = useState<ProcessMapVersionSummary[]>([])
  const [validationCases, setValidationCases] = useState<ValidationCase[]>([])
  const [agenticWorkflow, setAgenticWorkflow] = useState<AgenticWorkflow | null>(null)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('map')
  const [showVersionHistory, setShowVersionHistory] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load documents'))
  }, [])

  const documentId = documents?.[0]?.id ?? null

  const refetchAll = useCallback(() => {
    if (!documentId) return
    getProcessMap(documentId)
      .then((pm) => {
        setProcessMap(pm)
        setSelectedTaskId((prev) => (pm.tasks.some((t) => t.id === prev) ? prev : pm.tasks[0]?.id ?? null))
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load process map'))
    listIssues(documentId)
      .then(setIssues)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load issues'))
    listChangeRequests(documentId)
      .then(setChangeRequests)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load change requests'))
    listProcessMapVersions(documentId)
      .then(setVersions)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load version history'))
    listValidationCases(documentId)
      .then(setValidationCases)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load validation cases'))
    // Agentic workflow is a downstream, OPTIONAL artifact (see
    // skills/agentic-workflow-synthesis/SKILL.md) — a 404 here (none
    // generated yet) is expected for some documents and must not surface as
    // a page-level error like the other fetches above.
    getAgenticWorkflow(documentId)
      .then(setAgenticWorkflow)
      .catch(() => setAgenticWorkflow(null))
  }, [documentId])

  useEffect(() => {
    refetchAll()
  }, [refetchAll])

  const selectedTask = useMemo(
    () => processMap?.tasks.find((t) => t.id === selectedTaskId) ?? null,
    [processMap, selectedTaskId],
  )

  const pendingFeedbackCount =
    issues.filter((i) => i.status === 'open' || i.status === 'pending_review').length +
    changeRequests.filter((c) => c.status === 'pending').length

  function handleIssueUpdated(updated: Issue) {
    setIssues((prev) => prev.map((i) => (i.id === updated.id ? updated : i)))
  }

  function handleChangeRequestDecided(updated: ChangeRequest) {
    setChangeRequests((prev) => prev.map((c) => (c.id === updated.id ? updated : c)))
    if (updated.status === 'approved') {
      // Approving a change request produces a brand-new process map version —
      // refetch everything so the map, task panel, and version history all
      // reflect it immediately.
      refetchAll()
    }
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50 px-6 text-center">
        <div>
          <p className="text-sm font-medium text-rose-600">Couldn&rsquo;t load Process Printer</p>
          <p className="mt-2 text-xs text-slate-400">{error}</p>
          <p className="mt-2 text-xs text-slate-400">
            Is the backend running at the configured API base URL?
          </p>
        </div>
      </div>
    )
  }

  if (!documents || !processMap) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <p className="text-sm text-slate-400">Loading process map…</p>
      </div>
    )
  }

  const doc = documents[0]

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
        <div>
          <h1 className="text-sm font-semibold tracking-tight text-slate-900">Process Printer</h1>
          <p className="text-xs text-slate-400">
            {doc.title} · {doc.page_count} pages
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowVersionHistory((v) => !v)}
              data-testid="version-badge"
              className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              {processMap.version_label} ({processMap.status})
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>
            {showVersionHistory && (
              <div className="absolute right-0 z-10 mt-2 w-80 rounded-xl border border-slate-200 bg-white p-3 shadow-lg" data-testid="version-history">
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">Version history</p>
                <ul className="space-y-2 max-h-64 overflow-y-auto">
                  {versions.map((v) => (
                    <li key={v.id} className="rounded-lg border border-slate-100 px-2.5 py-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className={`font-medium ${v.is_current ? 'text-blue-700' : 'text-slate-700'}`}>
                          {v.version_label} {v.is_current && '(current)'}
                        </span>
                        <span className="text-[10px] text-slate-400">{new Date(v.created_at).toLocaleDateString()}</span>
                      </div>
                      {v.change_summary && <p className="mt-1 text-slate-500">{v.change_summary}</p>}
                      {v.changed_by && <p className="mt-0.5 text-[10px] text-slate-400">by {v.changed_by}</p>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <nav className="flex gap-1 rounded-xl bg-slate-100 p-1">
            {(
              [
                ['map', 'Process map'],
                ['feedback', `Feedback${pendingFeedbackCount > 0 ? ` (${pendingFeedbackCount})` : ''}`],
                ['validation', `Test scenarios (${validationCases.length})`],
                ['workflow', 'Agentic workflow'],
                ['chat', 'Chatbot'],
              ] as [Tab, string][]
            ).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                data-testid={`tab-${key}`}
                className={[
                  'rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
                  tab === key ? 'bg-white text-blue-700 shadow-sm' : 'text-slate-500 hover:text-slate-700',
                ].join(' ')}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="flex flex-1 overflow-hidden">
        {tab === 'map' && (
          <>
            <div className="flex-1 border-r border-slate-200">
              <ProcessMapView processMap={processMap} selectedTaskId={selectedTaskId} onSelectTask={setSelectedTaskId} />
            </div>
            <aside className="w-96 shrink-0 border-l border-slate-100 bg-white">
              <TaskDetailPanel task={selectedTask} />
            </aside>
          </>
        )}
        {tab === 'feedback' && (
          <div className="mx-auto w-full max-w-3xl overflow-y-auto">
            <div className="border-b border-slate-200 px-6 pt-6">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Gaps &amp; ambiguities</h2>
            </div>
            <IssuesPanel issues={issues} tasks={processMap.tasks} documentId={documentId!} onIssueUpdated={handleIssueUpdated} />
            <div className="border-y border-slate-200 px-6 pt-2">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Proposed changes from chat</h2>
            </div>
            <ChangeRequestsPanel documentId={documentId!} changeRequests={changeRequests} onDecided={handleChangeRequestDecided} />
          </div>
        )}
        {tab === 'validation' && (
          <div className="mx-auto w-full max-w-3xl">
            <ValidationPanel cases={validationCases} tasks={processMap.tasks} />
          </div>
        )}
        {tab === 'workflow' && <AgenticWorkflowPanel workflow={agenticWorkflow} />}
        {tab === 'chat' && (
          <div className="mx-auto w-full max-w-2xl">
            <ChatPanel documentId={documentId!} onChangesApplied={refetchAll} />
          </div>
        )}
      </main>
    </div>
  )
}
