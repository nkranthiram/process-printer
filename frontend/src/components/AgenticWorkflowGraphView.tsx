import { useMemo } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  MiniMap,
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

// MiniMap needs a real CSS color value, not a Tailwind class name — a tiny,
// explicit lookup (not a DOM read) mirrors AGENTIC_NODE_STYLE's dot colors
// in nodeStyles.ts as literal hex.
const DOT_COLOR: Record<string, string> = {
  deterministic: '#0ea5e9',
  agent: '#8b5cf6',
  agent_escalation: '#f59e0b',
  human: '#f43f5e',
  service: '#94a3b8',
  gateway: '#10b981',
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
          type: 'smoothstep', // right-angle connectors, the standard Camunda/n8n diagram convention
          pathOptions: { borderRadius: 8 },
          animated: false,
          style: { stroke: color, strokeWidth: 1.5 },
          labelStyle: { fill: '#475569', fontSize: 9.5, fontWeight: 500 },
          labelBgStyle: { fill: '#f8fafc', fillOpacity: 0.95 },
          labelBgPadding: [4, 2] as [number, number],
          markerEnd: { type: MarkerType.ArrowClosed, color, width: 16, height: 16 },
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
        fitViewOptions={{ padding: 0.12 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.3}
        maxZoom={1.5}
        nodesDraggable={false}
        defaultEdgeOptions={{ type: 'smoothstep' }}
      >
        <Background color="#e2e8f0" gap={24} />
        <Controls showInteractive={false} className="!bg-white !border-slate-200 !shadow-sm" />
        <MiniMap
          zoomable
          pannable
          className="!bg-white !border !border-slate-200"
          nodeColor={(n) => DOT_COLOR[(n.data as AgenticWorkflowGraphNodeData)?.node?.node_kind] ?? '#94a3b8'}
        />
      </ReactFlow>
    </div>
  )
}
