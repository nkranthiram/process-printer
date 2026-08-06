import { useEffect, useMemo, useState } from 'react'
import {
  getProcessMap,
  listDocuments,
  listIssues,
  listValidationCases,
  type DocumentSummary,
  type Issue,
  type ProcessMap,
  type ValidationCase,
} from './api'
import ProcessMapView from './components/ProcessMapView'
import TaskDetailPanel from './components/TaskDetailPanel'
import IssuesPanel from './components/IssuesPanel'
import ChatPanel from './components/ChatPanel'
import ValidationPanel from './components/ValidationPanel'

type Tab = 'map' | 'issues' | 'validation' | 'chat'

export default function App() {
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null)
  const [processMap, setProcessMap] = useState<ProcessMap | null>(null)
  const [issues, setIssues] = useState<Issue[]>([])
  const [validationCases, setValidationCases] = useState<ValidationCase[]>([])
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('map')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load documents'))
  }, [])

  const documentId = documents?.[0]?.id ?? null

  useEffect(() => {
    if (!documentId) return
    getProcessMap(documentId)
      .then((pm) => {
        setProcessMap(pm)
        setSelectedTaskId(pm.tasks[0]?.id ?? null)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load process map'))
    listIssues(documentId)
      .then(setIssues)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load issues'))
    listValidationCases(documentId)
      .then(setValidationCases)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load validation cases'))
  }, [documentId])

  const selectedTask = useMemo(
    () => processMap?.tasks.find((t) => t.id === selectedTaskId) ?? null,
    [processMap, selectedTaskId],
  )

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 px-6 text-center">
        <div>
          <p className="text-sm font-medium text-rose-300">Couldn&rsquo;t load Process Printer</p>
          <p className="mt-2 text-xs text-slate-500">{error}</p>
          <p className="mt-2 text-xs text-slate-600">
            Is the backend running at the configured API base URL?
          </p>
        </div>
      </div>
    )
  }

  if (!documents || !processMap) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950">
        <p className="text-sm text-slate-500">Loading process map…</p>
      </div>
    )
  }

  const doc = documents[0]

  return (
    <div className="flex h-screen flex-col bg-slate-950">
      <header className="flex items-center justify-between border-b border-slate-800 px-6 py-3">
        <div>
          <h1 className="text-sm font-semibold tracking-tight text-slate-50">Process Printer</h1>
          <p className="text-xs text-slate-500">
            {doc.title} · {doc.page_count} pages · process map {processMap.version_label} ({processMap.status})
          </p>
        </div>
        <nav className="flex gap-1 rounded-lg bg-slate-900 p-1">
          {(
            [
              ['map', 'Process map'],
              ['issues', `Gaps & ambiguities (${issues.length})`],
              ['validation', `Test scenarios (${validationCases.length})`],
              ['chat', 'Ask a question'],
            ] as [Tab, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              data-testid={`tab-${key}`}
              className={[
                'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                tab === key ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200',
              ].join(' ')}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      <main className="flex flex-1 overflow-hidden">
        {tab === 'map' && (
          <>
            <div className="flex-1 border-r border-slate-800">
              <ProcessMapView processMap={processMap} selectedTaskId={selectedTaskId} onSelectTask={setSelectedTaskId} />
            </div>
            <aside className="w-96 shrink-0">
              <TaskDetailPanel task={selectedTask} />
            </aside>
          </>
        )}
        {tab === 'issues' && (
          <div className="mx-auto w-full max-w-3xl">
            <IssuesPanel issues={issues} tasks={processMap.tasks} />
          </div>
        )}
        {tab === 'validation' && (
          <div className="mx-auto w-full max-w-3xl">
            <ValidationPanel cases={validationCases} tasks={processMap.tasks} />
          </div>
        )}
        {tab === 'chat' && (
          <div className="mx-auto w-full max-w-2xl">
            <ChatPanel documentId={documentId!} />
          </div>
        )}
      </main>
    </div>
  )
}
