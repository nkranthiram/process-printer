import { useState } from 'react'
import type { AgenticNodeKind, AgenticWorkflow, AgenticWorkflowNode } from '../api'

interface Props {
  workflow: AgenticWorkflow | null
}

const KIND_STYLE: Record<AgenticNodeKind, { label: string; badge: string }> = {
  deterministic: { label: 'Rule', badge: 'bg-sky-50 text-sky-700' },
  agent: { label: 'Agent', badge: 'bg-violet-50 text-violet-700' },
  agent_escalation: { label: 'Agent + escalation', badge: 'bg-amber-50 text-amber-700' },
  human: { label: 'Human', badge: 'bg-rose-50 text-rose-700' },
  service: { label: 'Service', badge: 'bg-slate-100 text-slate-600' },
  gateway: { label: 'Gateway', badge: 'bg-emerald-50 text-emerald-700' },
}

function NodeCard({ node }: { node: AgenticWorkflowNode }) {
  const [expanded, setExpanded] = useState(false)
  const style = KIND_STYLE[node.node_kind]
  const grounding = node.spec.grounding as { applicable?: boolean; reason?: string } | undefined
  const escalation = node.spec.confidence_escalation_trigger as
    | { threshold_set_id?: string; calibration_owner?: string }
    | undefined

  return (
    <li className="rounded-xl border border-slate-200 bg-white px-4 py-3.5 shadow-sm" data-testid="agentic-node">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.badge}`}>
              {style.label}
            </span>
            <h3 className="text-sm font-medium text-slate-800">{node.title}</h3>
          </div>
          {node.source_task_title && (
            <p className="mt-1 text-[11px] text-slate-400">from: {node.source_task_title}</p>
          )}
        </div>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="shrink-0 rounded-md border border-slate-200 px-2 py-1 text-[11px] text-slate-500 hover:bg-slate-50"
        >
          {expanded ? 'Hide spec' : 'View spec'}
        </button>
      </div>
      <p className="mt-2 text-xs text-slate-600">{node.goal}</p>

      {node.node_kind === 'agent_escalation' && escalation && (
        <p className="mt-2 text-[11px] text-amber-700">
          Confidence threshold: {escalation.threshold_set_id ?? 'unset'} — calibration owner:{' '}
          {escalation.calibration_owner ?? 'unassigned'}
        </p>
      )}
      {grounding?.applicable === false && (
        <p className="mt-2 text-[11px] text-slate-400">No grounding required — {grounding.reason}</p>
      )}

      {node.citations.length > 0 && (
        <p className="mt-2 text-[11px] text-slate-400">
          Cites {node.citations.length} claim{node.citations.length === 1 ? '' : 's'}: {node.citations.map((c) => c.subject).join(', ')}
        </p>
      )}

      {expanded && (
        <pre
          className="mt-3 max-h-80 overflow-auto rounded-lg bg-slate-50 p-3 text-[11px] leading-relaxed text-slate-700"
          data-testid="agentic-node-spec"
        >
          {JSON.stringify(node.spec, null, 2)}
        </pre>
      )}
    </li>
  )
}

export default function AgenticWorkflowPanel({ workflow }: Props) {
  if (workflow === null) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-slate-400">
        No agentic workflow generated yet for this document.
      </div>
    )
  }

  const kindCounts = workflow.nodes.reduce<Record<string, number>>((acc, n) => {
    acc[n.node_kind] = (acc[n.node_kind] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="h-full overflow-y-auto px-6 py-6" data-testid="agentic-workflow-panel">
      <p className="mb-1 text-xs text-slate-400">
        Generated from process map {workflow.process_map_version_label} ({workflow.generator_version}) — a
        builder-ready spec for automating this process, not a replacement for the process map above.
      </p>
      <p className="mb-4 text-[11px] text-slate-400">
        {Object.entries(kindCounts)
          .map(([kind, count]) => `${count} ${KIND_STYLE[kind as AgenticNodeKind]?.label ?? kind}`)
          .join(' · ')}
      </p>
      <ul className="space-y-3">
        {workflow.nodes.map((n) => (
          <NodeCard key={n.id} node={n} />
        ))}
      </ul>
    </div>
  )
}
