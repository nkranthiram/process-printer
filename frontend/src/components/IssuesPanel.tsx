import type { Issue, ProcessTask } from '../api'
import { ISSUE_TYPE_LABEL, ISSUE_TYPE_STYLE } from '../nodeStyles'

interface Props {
  issues: Issue[]
  tasks: ProcessTask[]
}

export default function IssuesPanel({ issues, tasks }: Props) {
  const taskById = new Map(tasks.map((t) => [t.id, t]))

  if (issues.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-slate-500">
        No open gaps or ambiguities logged for this document.
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto px-5 py-5" data-testid="issues-panel">
      <p className="mb-4 text-xs text-slate-500">
        Things the source document doesn&rsquo;t fully resolve — reviewed here, not
        blocking the process map. See each linked task for how it&rsquo;s handled today.
      </p>
      <ul className="space-y-3">
        {issues.map((issue) => {
          const style = ISSUE_TYPE_STYLE[issue.issue_type]
          const task = issue.process_task_id ? taskById.get(issue.process_task_id) : null
          return (
            <li key={issue.id} className={`rounded-lg border ${style.border} ${style.bg} px-4 py-3`} data-testid="issue-item">
              <div className="flex items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${style.accent} border ${style.border}`}>
                  {ISSUE_TYPE_LABEL[issue.issue_type]}
                </span>
                {task && <span className="text-[11px] text-slate-500">→ {task.title}</span>}
              </div>
              <h3 className="mt-1.5 text-sm font-medium text-slate-100">{issue.title}</h3>
              <p className="mt-1 text-xs leading-relaxed text-slate-400">{issue.description}</p>
              {issue.claim_refs.length > 0 && (
                <p className="mt-2 text-[11px] text-slate-500">
                  Related citations: {issue.claim_refs.map((c) => `p.${c.page}`).join(', ')}
                </p>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
