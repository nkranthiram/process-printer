import { Handle, Position, type NodeProps } from 'reactflow'
import { AGENTIC_NODE_STYLE } from '../nodeStyles'
import type { AgenticNodeKind, AgenticWorkflowNode } from '../api'

export interface AgenticWorkflowGraphNodeData {
  node: AgenticWorkflowNode
  selected: boolean
}

// Compact per-kind icons — plain geometric glyphs, not a full icon library —
// so every node reads at a glance without needing the label text. Detail
// (goal, spec, citations) lives entirely in the click-through side panel
// (AgenticNodeDetailPanel.tsx), matching how Camunda/n8n/UiPath keep
// on-canvas nodes minimal.
function KindIcon({ kind }: { kind: AgenticNodeKind }) {
  const common = { width: 14, height: 14, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2 }
  switch (kind) {
    case 'deterministic':
      return (
        <svg {...common}>
          <path d="M9 11l2 2 4-4" />
          <rect x="3" y="4" width="18" height="16" rx="2" />
        </svg>
      )
    case 'agent':
    case 'agent_escalation':
      return (
        <svg {...common}>
          <rect x="5" y="7" width="14" height="12" rx="2" />
          <path d="M9 3v4M15 3v4M9 13h.01M15 13h.01" />
        </svg>
      )
    case 'human':
      return (
        <svg {...common}>
          <circle cx="12" cy="8" r="3" />
          <path d="M5 20c0-3.9 3.1-7 7-7s7 3.1 7 7" />
        </svg>
      )
    case 'service':
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 004.6 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.6a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09A1.65 1.65 0 0015 4.6a1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
        </svg>
      )
    case 'gateway':
      return (
        <svg {...common}>
          <path d="M12 5v6M12 19v-6M5 12h6M13 12h6" />
        </svg>
      )
  }
}

const ESCALATION_BADGE = (
  <span className="absolute -right-1.5 -top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 text-[9px] font-bold text-white ring-2 ring-white">
    !
  </span>
)

export default function AgenticWorkflowGraphNode({ data }: NodeProps<AgenticWorkflowGraphNodeData>) {
  const { node, selected } = data
  const style = AGENTIC_NODE_STYLE[node.node_kind]

  if (node.node_kind === 'gateway') {
    // Diamond, per standard BPMN gateway convention (Camunda renders
    // gateways the same way) — visually distinct from every task/service/
    // human node at a glance, not just a different fill color.
    return (
      <div data-testid={`agentic-graph-node-${node.id}`} className="relative flex h-16 w-16 items-center justify-center">
        <Handle type="target" position={Position.Left} className="!bg-slate-300 !border-slate-400" />
        <div
          className={[
            'flex h-12 w-12 rotate-45 items-center justify-center rounded-md border-2 bg-white shadow-sm transition-all cursor-pointer hover:shadow-md',
            selected ? 'border-blue-500 ring-4 ring-blue-100' : style.border,
          ].join(' ')}
        >
          <div className={`-rotate-45 ${style.accent}`}>
            <KindIcon kind={node.node_kind} />
          </div>
        </div>
        <span className="pointer-events-none absolute top-[68px] w-32 -translate-x-1/2 text-center text-[10px] font-medium leading-tight text-slate-500 line-clamp-2">
          {node.title}
        </span>
        <Handle type="source" position={Position.Right} className="!bg-slate-300 !border-slate-400" />
      </div>
    )
  }

  const citationCount = node.citations.length

  return (
    <div
      data-testid={`agentic-graph-node-${node.id}`}
      className={[
        // Compact, icon-first card — no goal text, no source-task line, no
        // citation summary beyond a count; everything else lives in the
        // click-through detail panel. This, not layout spacing alone, is
        // what keeps a 16-node graph readable without excessive scrolling.
        'relative flex w-52 items-center gap-2.5 rounded-lg border-2 bg-white px-3 py-2.5 shadow-sm transition-all cursor-pointer hover:shadow-md',
        selected ? 'border-blue-500 ring-4 ring-blue-100' : style.border,
      ].join(' ')}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-300 !border-slate-400" />
      {node.node_kind === 'agent_escalation' && ESCALATION_BADGE}
      <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md ${style.bg} ${style.accent}`}>
        <KindIcon kind={node.node_kind} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[13px] font-medium leading-tight text-slate-800">{node.title}</div>
        {citationCount > 0 && (
          <div className="mt-0.5 text-[10px] text-slate-400">
            {citationCount} citation{citationCount === 1 ? '' : 's'}
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-slate-300 !border-slate-400" />
    </div>
  )
}
