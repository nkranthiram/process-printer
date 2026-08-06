import { useMemo } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  type Edge,
  type Node,
} from 'reactflow'
import 'reactflow/dist/style.css'
import type { ProcessMap } from '../api'
import TaskNode, { type TaskNodeData } from './TaskNode'

const nodeTypes = { task: TaskNode }

interface Props {
  processMap: ProcessMap
  selectedTaskId: string | null
  onSelectTask: (taskId: string) => void
}

export default function ProcessMapView({ processMap, selectedTaskId, onSelectTask }: Props) {
  const nodes: Node<TaskNodeData>[] = useMemo(
    () =>
      processMap.tasks.map((task) => ({
        id: task.id,
        type: 'task',
        position: { x: task.position_x, y: task.position_y },
        data: { task, selected: task.id === selectedTaskId },
      })),
    [processMap.tasks, selectedTaskId],
  )

  const edges: Edge[] = useMemo(
    () =>
      processMap.edges.map((e) => ({
        id: e.id,
        source: e.from_task_id,
        target: e.to_task_id,
        label: e.condition_label ?? undefined,
        animated: false,
        style: { stroke: '#475569', strokeWidth: 1.5 },
        labelStyle: { fill: '#cbd5e1', fontSize: 11 },
        labelBgStyle: { fill: '#0f172a', fillOpacity: 0.85 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#475569' },
      })),
    [processMap.edges],
  )

  return (
    <div data-testid="process-map-canvas" className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelectTask(node.id)}
        fitView
        proOptions={{ hideAttribution: true }}
        minZoom={0.3}
      >
        <Background color="#1e293b" gap={24} />
        <Controls showInteractive={false} className="!bg-slate-900 !border-slate-700" />
      </ReactFlow>
    </div>
  )
}
