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
import { computeLayeredLayout } from '../layout'
import TaskNode, { type TaskNodeData } from './TaskNode'

const nodeTypes = { task: TaskNode }

interface Props {
  processMap: ProcessMap
  selectedTaskId: string | null
  onSelectTask: (taskId: string) => void
}

export default function ProcessMapView({ processMap, selectedTaskId, onSelectTask }: Props) {
  // Positions are recomputed client-side from the graph structure rather than
  // trusted from the backend's stored grid coordinates — see layout.ts for why
  // (fixes the text/box overlap from PROGRESS.md task 22, and self-heals when
  // a change request adds/removes a task).
  const positions = useMemo(
    () => computeLayeredLayout(processMap.tasks, processMap.edges),
    [processMap.tasks, processMap.edges],
  )

  const nodes: Node<TaskNodeData>[] = useMemo(
    () =>
      processMap.tasks.map((task) => ({
        id: task.id,
        type: 'task',
        position: positions.get(task.id) ?? { x: task.position_x, y: task.position_y },
        data: { task, selected: task.id === selectedTaskId },
      })),
    [processMap.tasks, positions, selectedTaskId],
  )

  const edges: Edge[] = useMemo(
    () =>
      processMap.edges.map((e) => ({
        id: e.id,
        source: e.from_task_id,
        target: e.to_task_id,
        label: e.condition_label ?? undefined,
        animated: false,
        style: { stroke: '#94a3b8', strokeWidth: 1.5 },
        labelStyle: { fill: '#475569', fontSize: 11, fontWeight: 500 },
        labelBgStyle: { fill: '#f8fafc', fillOpacity: 0.95 },
        labelBgPadding: [6, 3] as [number, number],
        markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
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
        minZoom={0.2}
        nodesDraggable={false}
      >
        <Background color="#e2e8f0" gap={28} />
        <Controls showInteractive={false} className="!bg-white !border-slate-200 !shadow-sm" />
      </ReactFlow>
    </div>
  )
}
