import type { AgenticWorkflowEdge, AgenticWorkflowNode, ProcessEdge, ProcessTask } from './api'

/** Layered top-to-bottom auto-layout, computed client-side.
 *
 * The backend stores a coarse grid position per task (see backend/app/seed.py),
 * which was spaced tightly enough that node text overlapped once real titles
 * (which vary in length) were rendered — see PROGRESS.md task 22. Rather than
 * trust stored positions, this recomputes layout from the actual graph
 * structure every render: each task's rank is its longest-path distance from
 * the root, tasks in the same rank are laid out in a row with generous fixed
 * spacing, and the whole thing self-heals when a change request adds/removes
 * a task — no backend position math to keep in sync.
 */

const COLUMN_WIDTH = 300 // vertical distance between ranks (this is a top-to-bottom flow)
const ROW_WIDTH = 340 // horizontal distance between siblings in the same rank
const NODE_WIDTH = 280

export interface LayoutPosition {
  x: number
  y: number
}

interface GraphEdgeLike {
  from: string
  to: string
}

/** The actual layout algorithm, generalized over any node-id list + edge list
 * so it can lay out a ProcessMap's tasks/edges OR an AgenticWorkflow's
 * nodes/edges identically — both are DAGs that need the same top-to-bottom,
 * self-healing, no-overlap treatment (see module docstring above). */
function computeLayeredLayoutGeneric(nodeIds: string[], edges: GraphEdgeLike[]): Map<string, LayoutPosition> {
  const positions = new Map<string, LayoutPosition>()
  if (nodeIds.length === 0) return positions

  const idSet = new Set(nodeIds)
  const outgoing = new Map<string, string[]>(nodeIds.map((id) => [id, []]))
  const incomingCount = new Map<string, number>(nodeIds.map((id) => [id, 0]))

  for (const e of edges) {
    if (!idSet.has(e.from) || !idSet.has(e.to)) continue
    outgoing.get(e.from)!.push(e.to)
    incomingCount.set(e.to, (incomingCount.get(e.to) ?? 0) + 1)
  }

  // Rank = longest path from any root (node with no incoming edges). Longest-
  // path (not shortest/BFS) so a node with two incoming edges from different
  // ranks always sits below both — avoids edges pointing "backwards" visually.
  const rank = new Map<string, number>(nodeIds.map((id) => [id, 0]))
  const roots = nodeIds.filter((id) => (incomingCount.get(id) ?? 0) === 0)
  const startNodes = roots.length > 0 ? roots : [nodeIds[0]]

  // Iterative relaxation (bounded by node count) rather than recursive DFS —
  // safe even if validation somehow let a cycle through; it just stops
  // improving after N passes instead of infinite-looping.
  for (let pass = 0; pass < nodeIds.length + 1; pass++) {
    let changed = false
    for (const id of nodeIds) {
      const r = rank.get(id)!
      for (const next of outgoing.get(id) ?? []) {
        if ((rank.get(next) ?? 0) < r + 1) {
          rank.set(next, r + 1)
          changed = true
        }
      }
    }
    if (!changed) break
  }
  void startNodes // ranks are computed globally via relaxation, not per-root traversal

  const byRank = new Map<number, string[]>()
  for (const id of nodeIds) {
    const r = rank.get(id) ?? 0
    if (!byRank.has(r)) byRank.set(r, [])
    byRank.get(r)!.push(id)
  }

  const maxRowLength = Math.max(...[...byRank.values()].map((ids) => ids.length))
  const canvasWidth = maxRowLength * ROW_WIDTH

  for (const [r, ids] of byRank) {
    const rowWidth = ids.length * ROW_WIDTH
    const startX = (canvasWidth - rowWidth) / 2 + ROW_WIDTH / 2 - NODE_WIDTH / 2
    ids.forEach((id, i) => {
      positions.set(id, { x: startX + i * ROW_WIDTH, y: r * COLUMN_WIDTH })
    })
  }

  return positions
}

export function computeLayeredLayout(tasks: ProcessTask[], edges: ProcessEdge[]): Map<string, LayoutPosition> {
  return computeLayeredLayoutGeneric(
    tasks.map((t) => t.id),
    edges.map((e) => ({ from: e.from_task_id, to: e.to_task_id })),
  )
}

/** Same algorithm, applied to an AgenticWorkflow's nodes/edges instead of a
 * ProcessMap's tasks/edges — the agentic workflow view needs the identical
 * spacious, self-healing layout the process map already has (see
 * AgenticWorkflowGraphView.tsx), not a second, divergent implementation. */
export function computeAgenticWorkflowLayout(
  nodes: AgenticWorkflowNode[],
  edges: AgenticWorkflowEdge[],
): Map<string, LayoutPosition> {
  return computeLayeredLayoutGeneric(
    nodes.map((n) => n.id),
    edges.map((e) => ({ from: e.from_node_id, to: e.to_node_id })),
  )
}
