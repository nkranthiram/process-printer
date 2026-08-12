import dagre from 'dagre'
import type { AgenticWorkflowEdge, AgenticWorkflowNode, ProcessEdge, ProcessTask } from './api'

/** Auto-layout for both graphs, computed client-side via dagre.
 *
 * PREVIOUSLY a hand-rolled "rank = longest path from a root, iterative
 * relaxation" algorithm lived here. It had a real, user-visible bug: the
 * agentic workflow contains a genuine cycle (HUM-01 <-> HUM-02, the human
 * escalation/request-more-info loop; BR-01 <-> HUM-01 too) and longest-path
 * relaxation has no cycle handling — each pass around the cycle pushed the
 * rank higher, and the bounded pass-count cap (node count + 1) just stopped
 * it at an arbitrary, huge number (observed: rank 94 for nodes that should
 * be ~4-8 deep). That stretched a couple of edges across an enormous empty
 * gap — the "edges spanning several pages" the user actually saw, in BOTH
 * the vertical and horizontal orientations tried before this fix (the bug
 * was in the ranking step, not the orientation).
 *
 * dagre breaks cycles properly (a feedback-arc-set pass before ranking,
 * standard for layered graph drawing — same class of algorithm Camunda/
 * n8n/UiPath actually use under the hood) and is a maintained, tested
 * library rather than a second hand-rolled implementation to keep re-fixing.
 */

export interface LayoutPosition {
  x: number
  y: number
}

interface GraphEdgeLike {
  from: string
  to: string
}

interface DagreOptions {
  direction: 'TB' | 'LR'
  nodeWidth: number
  nodeHeight: number
  rankSep: number // gap between ranks (edge-to-edge, not center-to-center)
  nodeSep: number // gap between siblings within a rank
}

function computeDagreLayout(nodeIds: string[], edges: GraphEdgeLike[], options: DagreOptions): Map<string, LayoutPosition> {
  const positions = new Map<string, LayoutPosition>()
  if (nodeIds.length === 0) return positions

  const g = new dagre.graphlib.Graph()
  g.setGraph({
    rankdir: options.direction,
    ranksep: options.rankSep,
    nodesep: options.nodeSep,
    marginx: 20,
    marginy: 20,
  })
  g.setDefaultEdgeLabel(() => ({}))

  for (const id of nodeIds) {
    g.setNode(id, { width: options.nodeWidth, height: options.nodeHeight })
  }

  const idSet = new Set(nodeIds)
  for (const e of edges) {
    if (!idSet.has(e.from) || !idSet.has(e.to)) continue
    g.setEdge(e.from, e.to)
  }

  dagre.layout(g)

  for (const id of nodeIds) {
    const n = g.node(id)
    // dagre positions are node CENTERS; React Flow positions are top-left
    // corners — convert once here so every caller gets top-left directly.
    positions.set(id, { x: n.x - options.nodeWidth / 2, y: n.y - options.nodeHeight / 2 })
  }

  return positions
}

/** Process map: unchanged top-to-bottom orientation, sized for TaskNode.tsx's
 * fixed 264x104 card. */
export function computeLayeredLayout(tasks: ProcessTask[], edges: ProcessEdge[]): Map<string, LayoutPosition> {
  return computeDagreLayout(
    tasks.map((t) => t.id),
    edges.map((e) => ({ from: e.from_task_id, to: e.to_task_id })),
    { direction: 'TB', nodeWidth: 264, nodeHeight: 104, rankSep: 170, nodeSep: 60 },
  )
}

/** Agentic workflow: left-to-right, sized for AgenticWorkflowGraphNode.tsx's
 * compact card (rectangular nodes) / diamond (gateway nodes) — see that file
 * for why left-to-right specifically: a wide flow reads better than a tall
 * one for a 15+ node graph, matching Camunda/n8n/UiPath's default. */
export function computeAgenticWorkflowLayout(
  nodes: AgenticWorkflowNode[],
  edges: AgenticWorkflowEdge[],
): Map<string, LayoutPosition> {
  return computeDagreLayout(
    nodes.map((n) => n.id),
    edges.map((e) => ({ from: e.from_node_id, to: e.to_node_id })),
    { direction: 'LR', nodeWidth: 208, nodeHeight: 64, rankSep: 90, nodeSep: 36 },
  )
}
