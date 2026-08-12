import { useMemo } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  type Edge,
  type Node,
} from 'reactflow'
import 'reactflow/dist/style.css'
import type { AgenticWorkflow } from '../api'
import { computeAgenticWorkflowLayout } from '../layout'
import AgenticWorkflowGraphNode, { type AgenticWorkflowGraphNodeData } from './AgenticWorkflowGraphNode'

const nodeTypes = { agenticNode: AgenticWorkflowGraphNode }

interface Props {
  workflow: AgenticWorkflow
  selectedNodeId: string | null
  onSelectNode: (nodeId: string) => void
}

// Edge coloring makes the escalation-scoping non-negotiable (see
// skills/agentic-workflow-synthesis/SKILL.md) visible at a glance, not just
// enforced silently by the backend validator: a deterministic decline stays
// slate (routine, auto-processed), while any agent-judgment-caused adverse
// outcome is amber — the same color agent_escalation nodes use — so a
// reviewer can visually trace "every amber edge must end at a human or
// gateway node" without reading the spec JSON.
function edgeColor(conditionLabel: string | null): string {
  const label = (conditionLabel ?? '').toLowerCase()
  if (label.includes('agent-judgment adverse') || label.includes('escalat')) return '#d97706' // amber-600
  if (label.includes('deterministic decline')) return '#64748b' // slate-500
  return '#94a3b8' // slate-400, default
}

export default function AgenticWorkflowGraphView({ workflow, selectedNodeId, onSelectNode }: Props) {
  const positions = useMemo(
    () => computeAgenticWorkflowLayout(workflow.nodes, workflow.edges),
    [workflow.nodes, workflow.edges],
  )

  const nodes: Node<AgenticWorkflowGraphNodeData>[] = useMemo(
    () =>
      workflow.nodes.map((node) => ({
        id: node.id,
        type: 'agenticNode',
        position: positions.get(node.id) ?? { x: 0, y: 0 },
        data: { node, selected: node.id === selectedNodeId },
      })),
    [workflow.nodes, positions, selectedNodeId],
  )

  const edges: Edge[] = useMemo(
    () =>
      workflow.edges.map((e) => {
        const color = edgeColor(e.condition_label)
        return {
          id: e.id,
          source: e.from_node_id,
          target: e.to_node_id,
          label: e.condition_label ?? undefined,
          animated: false,
          style: { stroke: color, strokeWidth: 1.5 },
          labelStyle: { fill: '#475569', fontSize: 10, fontWeight: 500 },
          labelBgStyle: { fill: '#f8fafc', fillOpacity: 0.95 },
          labelBgPadding: [5, 2] as [number, number],
          markerEnd: { type: MarkerType.ArrowClosed, color },
        }
      }),
    [workflow.edges],
  )

  return (
    <div data-testid="agentic-workflow-canvas" className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelectNode(node.id)}
        fitView
        proOptions={{ hideAttribution: true }}
        minZoom={0.15}
        nodesDraggable={false}
      >
        <Background color="#e2e8f0" gap={28} />
        <Controls showInteractive={false} className="!bg-white !border-slate-200 !shadow-sm" />
      </ReactFlow>
    </div>
  )
}
