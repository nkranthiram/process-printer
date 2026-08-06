import { Handle, Position, type NodeProps } from 'reactflow'
import { NODE_TYPE_LABEL, NODE_TYPE_STYLE } from '../nodeStyles'
import type { ProcessTask } from '../api'

export interface TaskNodeData {
  task: ProcessTask
  selected: boolean
}

export default function TaskNode({ data }: NodeProps<TaskNodeData>) {
  const { task, selected } = data
  const style = NODE_TYPE_STYLE[task.node_type]

  return (
    <div
      data-testid={`task-node-${task.id}`}
      className={[
        // Fixed width + min-height + line-clamp keeps every node a predictable
        // size regardless of title length, so the layered layout's fixed
        // spacing never has to guess — this is what actually prevents overlap,
        // not just wider gaps (see layout.ts).
        'w-64 min-h-[104px] rounded-2xl border-2 bg-white px-4 py-3.5 shadow-sm transition-all cursor-pointer hover:shadow-md',
        selected ? 'border-blue-500 ring-4 ring-blue-100' : style.border,
      ].join(' ')}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-300 !border-slate-400" />
      <div className="flex items-center gap-2 mb-2">
        <span className={`h-2 w-2 rounded-full ${style.dot}`} />
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.bg} ${style.accent}`}>
          {NODE_TYPE_LABEL[task.node_type]}
        </span>
      </div>
      <div className="text-sm font-semibold text-slate-800 leading-snug line-clamp-3">{task.title}</div>
      {task.citations.length > 0 && (
        <div className="mt-2.5 flex items-center gap-1 text-[11px] text-slate-400">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 12h6M9 16h6M9 8h1M5 4h10l4 4v12a1 1 0 01-1 1H5a1 1 0 01-1-1V5a1 1 0 011-1z" />
          </svg>
          {task.citations.length} source{task.citations.length === 1 ? '' : 's'} cited
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-slate-300 !border-slate-400" />
    </div>
  )
}
