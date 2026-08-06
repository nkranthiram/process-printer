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
        'w-64 rounded-xl border px-4 py-3 shadow-lg backdrop-blur-sm transition-all cursor-pointer',
        style.bg,
        selected ? 'border-white/70 ring-2 ring-white/30' : style.border,
      ].join(' ')}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-500" />
      <div className="flex items-center gap-2 mb-1.5">
        <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
        <span className={`text-[10px] font-medium uppercase tracking-wide ${style.accent}`}>
          {NODE_TYPE_LABEL[task.node_type]}
        </span>
      </div>
      <div className="text-sm font-semibold text-slate-50 leading-snug">{task.title}</div>
      {task.citations.length > 0 && (
        <div className="mt-2 text-[11px] text-slate-400">
          {task.citations.length} source{task.citations.length === 1 ? '' : 's'} cited
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-slate-500" />
    </div>
  )
}
