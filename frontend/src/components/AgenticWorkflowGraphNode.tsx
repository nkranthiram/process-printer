import { Handle, Position, type NodeProps } from 'reactflow'
import { AGENTIC_NODE_LABEL, AGENTIC_NODE_STYLE } from '../nodeStyles'
import type { AgenticWorkflowNode } from '../api'

export interface AgenticWorkflowGraphNodeData {
  node: AgenticWorkflowNode
  selected: boolean
}

export default function AgenticWorkflowGraphNode({ data }: NodeProps<AgenticWorkflowGraphNodeData>) {
  const { node, selected } = data
  const style = AGENTIC_NODE_STYLE[node.node_kind]

  return (
    <div
      data-testid={`agentic-graph-node-${node.id}`}
      className={[
        // Same fixed-size, no-overlap discipline as TaskNode.tsx.
        'w-64 min-h-[104px] rounded-2xl border-2 bg-white px-4 py-3.5 shadow-sm transition-all cursor-pointer hover:shadow-md',
        selected ? 'border-blue-500 ring-4 ring-blue-100' : style.border,
      ].join(' ')}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-300 !border-slate-400" />
      <div className="mb-2 flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${style.dot}`} />
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.bg} ${style.accent}`}>
          {AGENTIC_NODE_LABEL[node.node_kind]}
        </span>
      </div>
      <div className="text-sm font-semibold leading-snug text-slate-800 line-clamp-3">{node.title}</div>
      {node.source_task_title && (
        <div className="mt-1.5 line-clamp-1 text-[10px] text-slate-400">from: {node.source_task_title}</div>
      )}
      {node.citations.length > 0 && (
        <div className="mt-2.5 flex items-center gap-1 text-[11px] text-slate-400">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 12h6M9 16h6M9 8h1M5 4h10l4 4v12a1 1 0 01-1 1H5a1 1 0 01-1-1V5a1 1 0 011-1z" />
          </svg>
          {node.citations.length} source{node.citations.length === 1 ? '' : 's'} cited
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-slate-300 !border-slate-400" />
    </div>
  )
}
