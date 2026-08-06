import { useState } from 'react'
import type { ProcessTask } from '../api'
import { NODE_TYPE_LABEL, NODE_TYPE_STYLE } from '../nodeStyles'

interface Props {
  task: ProcessTask | null
}

export default function TaskDetailPanel({ task }: Props) {
  const [expandedCitation, setExpandedCitation] = useState<string | null>(null)

  if (!task) {
    return (
      <div className="flex h-full items-center justify-center text-center px-6">
        <p className="text-sm text-slate-400">
          Select a task in the process map to see its description and citations.
        </p>
      </div>
    )
  }

  const style = NODE_TYPE_STYLE[task.node_type]

  return (
    <div className="flex h-full flex-col overflow-y-auto px-6 py-6" data-testid="task-detail-panel">
      <span className={`inline-block w-fit rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.bg} ${style.accent}`}>
        {NODE_TYPE_LABEL[task.node_type]}
      </span>
      <h2 className="mt-3 text-lg font-semibold text-slate-900">{task.title}</h2>
      <p className="mt-3 text-sm leading-relaxed text-slate-600 whitespace-pre-line">{task.description}</p>

      <div className="mt-7">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Citations ({task.citations.length})
        </h3>
        {task.citations.length === 0 && (
          <p className="mt-2 text-xs text-slate-400">
            This is a structural step with no directly cited source text.
          </p>
        )}
        <ul className="mt-3 space-y-2">
          {task.citations.map((c) => {
            const isOpen = expandedCitation === c.claim_id
            return (
              <li key={c.claim_id} className="rounded-xl border border-slate-200 bg-slate-50/70 overflow-hidden">
                <button
                  type="button"
                  data-testid={`citation-toggle-${c.claim_id}`}
                  onClick={() => setExpandedCitation(isOpen ? null : c.claim_id)}
                  className="flex w-full items-center justify-between gap-2 px-3.5 py-2.5 text-left hover:bg-slate-100/80 transition-colors"
                >
                  <span className="text-xs text-slate-700">{c.statement}</span>
                  <span className="shrink-0 rounded-full bg-white px-1.5 py-0.5 text-[10px] font-medium text-slate-400 border border-slate-200">
                    p.{c.page}
                  </span>
                </button>
                {isOpen && (
                  <div
                    data-testid={`citation-detail-${c.claim_id}`}
                    className="border-t border-slate-200 bg-white px-3.5 py-2.5 text-[11px] leading-relaxed text-slate-500"
                  >
                    <p className="italic text-slate-600">&ldquo;{c.raw_quote}&rdquo;</p>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-slate-400">
                      <span>Page {c.page}</span>
                      {c.section_path && <span>{c.section_path}</span>}
                      <span>{c.claim_type} · {c.modality}</span>
                      <span>confidence {(c.extraction_confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
