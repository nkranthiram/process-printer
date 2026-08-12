import { useState, type ReactNode } from 'react'
import type { AgenticWorkflowNode } from '../api'
import { AGENTIC_NODE_LABEL, AGENTIC_NODE_STYLE } from '../nodeStyles'

interface Props {
  node: AgenticWorkflowNode | null
}

function SpecField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="mt-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</h3>
      <div className="mt-1.5 text-sm leading-relaxed text-slate-600">{children}</div>
    </div>
  )
}

export default function AgenticNodeDetailPanel({ node }: Props) {
  const [showRaw, setShowRaw] = useState(false)

  if (!node) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center">
        <p className="text-sm text-slate-400">Select a node in the agentic workflow to see its full spec.</p>
      </div>
    )
  }

  const style = AGENTIC_NODE_STYLE[node.node_kind]
  const spec = node.spec as Record<string, unknown>
  const grounding = spec.grounding as { applicable?: boolean; reason?: string; fabrication_check?: string; misapplication_check?: string } | undefined
  const escalation = spec.confidence_escalation_trigger as
    | { threshold_set_id?: string; calibration_dataset_version?: string; calibration_owner?: string; revalidation_trigger?: string }
    | undefined
  const decisionLogic = spec.decision_logic ?? spec.authority_boundary ?? spec.decision_logic_authority_boundary
  const inputs = spec.inputs
  const outputs = spec.outputs
  const downstreamEdges = spec.downstream_edges as unknown[] | undefined

  return (
    <div className="flex h-full flex-col overflow-y-auto px-6 py-6" data-testid="agentic-node-detail-panel">
      <span className={`inline-block w-fit rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.bg} ${style.accent}`}>
        {AGENTIC_NODE_LABEL[node.node_kind]}
      </span>
      <h2 className="mt-3 text-lg font-semibold text-slate-900">{node.title}</h2>
      {node.source_task_title && (
        <p className="mt-1 text-xs text-slate-400">Derived from process-map task: {node.source_task_title}</p>
      )}
      <p className="mt-3 text-sm leading-relaxed text-slate-600">{node.goal}</p>

      {decisionLogic != null && (
        <SpecField label="Decision logic / authority boundary">
          <p className="whitespace-pre-line">{String(decisionLogic)}</p>
        </SpecField>
      )}

      {grounding && (
        <SpecField label="Grounding">
          {grounding.applicable === false ? (
            <p className="text-slate-400">Not applicable — {grounding.reason}</p>
          ) : (
            <ul className="space-y-1">
              <li>
                <span className="font-medium text-slate-700">Fabrication check: </span>
                {grounding.fabrication_check ?? '—'}
              </li>
              <li>
                <span className="font-medium text-slate-700">Misapplication check: </span>
                {grounding.misapplication_check ?? '—'}
              </li>
            </ul>
          )}
        </SpecField>
      )}

      {node.node_kind === 'agent_escalation' && escalation && (
        <SpecField label="Confidence / escalation trigger">
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
            <p>
              Threshold set: <span className="font-medium">{escalation.threshold_set_id ?? 'unset'}</span>
            </p>
            <p className="mt-1">
              Calibration owner: <span className="font-medium">{escalation.calibration_owner ?? 'unassigned'}</span>
            </p>
            {escalation.calibration_dataset_version && (
              <p className="mt-1">Calibration dataset: {escalation.calibration_dataset_version}</p>
            )}
            {escalation.revalidation_trigger && <p className="mt-1">Revalidate on: {escalation.revalidation_trigger}</p>}
          </div>
        </SpecField>
      )}

      {inputs != null && (
        <SpecField label="Inputs">
          <pre className="overflow-auto rounded-lg bg-slate-50 p-2.5 text-[11px] leading-relaxed text-slate-600">
            {typeof inputs === 'string' ? inputs : JSON.stringify(inputs, null, 2)}
          </pre>
        </SpecField>
      )}

      {outputs != null && (
        <SpecField label="Outputs">
          <pre className="overflow-auto rounded-lg bg-slate-50 p-2.5 text-[11px] leading-relaxed text-slate-600">
            {typeof outputs === 'string' ? outputs : JSON.stringify(outputs, null, 2)}
          </pre>
        </SpecField>
      )}

      {downstreamEdges && downstreamEdges.length > 0 && (
        <SpecField label="Downstream edges">
          <ul className="list-disc space-y-0.5 pl-4">
            {downstreamEdges.map((d, i) => (
              <li key={i}>{String(d)}</li>
            ))}
          </ul>
        </SpecField>
      )}

      <div className="mt-6">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Citations ({node.citations.length})
        </h3>
        {node.citations.length === 0 && (
          <p className="mt-2 text-xs text-slate-400">
            This is a structural node with no directly cited source text.
          </p>
        )}
        <ul className="mt-3 space-y-2">
          {node.citations.map((c) => (
            <li key={c.claim_id} className="rounded-xl border border-slate-200 bg-slate-50/70 px-3.5 py-2.5">
              <p className="text-[10px] font-medium uppercase tracking-wide text-slate-400">{c.subject}</p>
              <p className="mt-1 text-xs text-slate-700">{c.statement}</p>
              <p className="mt-1.5 italic text-[11px] text-slate-500">&ldquo;{c.raw_quote}&rdquo;</p>
              <p className="mt-1.5 text-[10px] text-slate-400">
                p.{c.page} · {c.claim_type} · {c.modality} · confidence {(c.extraction_confidence * 100).toFixed(0)}%
              </p>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-6 border-t border-slate-100 pt-4">
        <button
          type="button"
          onClick={() => setShowRaw((v) => !v)}
          className="rounded-md border border-slate-200 px-2.5 py-1 text-[11px] text-slate-500 hover:bg-slate-50"
        >
          {showRaw ? 'Hide raw spec JSON' : 'View raw spec JSON'}
        </button>
        {showRaw && (
          <pre
            data-testid="agentic-node-raw-spec"
            className="mt-3 max-h-80 overflow-auto rounded-lg bg-slate-50 p-3 text-[11px] leading-relaxed text-slate-700"
          >
            {JSON.stringify(node.spec, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}
