import { describe, expect, it } from 'vitest'
import { computeAgenticWorkflowLayout, computeLayeredLayout } from './layout'
import type { AgenticWorkflowEdge, AgenticWorkflowNode, ProcessEdge, ProcessTask } from './api'

function task(id: string): ProcessTask {
  return {
    id,
    node_type: 'classification',
    title: id,
    description: '',
    position_x: 0,
    position_y: 0,
    citations: [],
  }
}

function edge(from: string, to: string): ProcessEdge {
  return { id: `${from}-${to}`, from_task_id: from, to_task_id: to, condition_label: null }
}

describe('computeLayeredLayout (process map, top-to-bottom)', () => {
  it('places a linear chain in strictly increasing rows with no two nodes overlapping', () => {
    const tasks = [task('a'), task('b'), task('c')]
    const edges = [edge('a', 'b'), edge('b', 'c')]
    const positions = computeLayeredLayout(tasks, edges)

    expect(positions.get('a')!.y).toBeLessThan(positions.get('b')!.y)
    expect(positions.get('b')!.y).toBeLessThan(positions.get('c')!.y)
  })

  it('places a fan-out (one node, two children) at the same rank with different x', () => {
    const tasks = [task('root'), task('left'), task('right')]
    const edges = [edge('root', 'left'), edge('root', 'right')]
    const positions = computeLayeredLayout(tasks, edges)

    expect(positions.get('left')!.y).toBe(positions.get('right')!.y)
    expect(positions.get('left')!.x).not.toBe(positions.get('right')!.x)
    // and both children must be strictly below the root
    expect(positions.get('root')!.y).toBeLessThan(positions.get('left')!.y)
  })

  it('a node with two incoming edges from different ranks sits below BOTH predecessors', () => {
    // a -> b -> d, a -> d  (d has two parents at different depths)
    const tasks = [task('a'), task('b'), task('d')]
    const edges = [edge('a', 'b'), edge('b', 'd'), edge('a', 'd')]
    const positions = computeLayeredLayout(tasks, edges)

    expect(positions.get('d')!.y).toBeGreaterThan(positions.get('a')!.y)
    expect(positions.get('d')!.y).toBeGreaterThan(positions.get('b')!.y)
  })

  it('no two nodes ever land on the exact same (x, y)', () => {
    const tasks = [task('a'), task('b'), task('c'), task('d'), task('e')]
    const edges = [edge('a', 'b'), edge('a', 'c'), edge('a', 'd'), edge('a', 'e')]
    const positions = computeLayeredLayout(tasks, edges)

    const seen = new Set<string>()
    for (const t of tasks) {
      const p = positions.get(t.id)!
      const key = `${p.x},${p.y}`
      expect(seen.has(key)).toBe(false)
      seen.add(key)
    }
  })

  it('returns an empty map for an empty task list without throwing', () => {
    expect(computeLayeredLayout([], []).size).toBe(0)
  })
})

function agenticNode(id: string): AgenticWorkflowNode {
  return {
    id, node_kind: 'service', title: id, goal: '', source_task_title: null, spec: {}, citations: [],
  }
}

function agenticEdge(from: string, to: string): AgenticWorkflowEdge {
  return { id: `${from}-${to}`, from_node_id: from, to_node_id: to, condition_label: null }
}

// The agentic workflow is laid out LEFT-TO-RIGHT (rank progresses along x),
// deliberately different from the process map's top-to-bottom orientation —
// see layout.ts's computeAgenticWorkflowLayout for why.
describe('computeAgenticWorkflowLayout (agentic workflow, left-to-right)', () => {
  it('places a linear chain of agentic nodes in strictly increasing columns', () => {
    const nodes = [agenticNode('a'), agenticNode('b'), agenticNode('c')]
    const edges = [agenticEdge('a', 'b'), agenticEdge('b', 'c')]
    const positions = computeAgenticWorkflowLayout(nodes, edges)

    expect(positions.get('a')!.x).toBeLessThan(positions.get('b')!.x)
    expect(positions.get('b')!.x).toBeLessThan(positions.get('c')!.x)
  })

  it('a node with two incoming edges from different ranks sits to the right of both predecessors', () => {
    const nodes = [agenticNode('a'), agenticNode('b'), agenticNode('d')]
    const edges = [agenticEdge('a', 'b'), agenticEdge('b', 'd'), agenticEdge('a', 'd')]
    const positions = computeAgenticWorkflowLayout(nodes, edges)

    expect(positions.get('d')!.x).toBeGreaterThan(positions.get('a')!.x)
    expect(positions.get('d')!.x).toBeGreaterThan(positions.get('b')!.x)
  })

  it('places a fan-out at the same rank (same x) with different y', () => {
    const nodes = [agenticNode('root'), agenticNode('left'), agenticNode('right')]
    const edges = [agenticEdge('root', 'left'), agenticEdge('root', 'right')]
    const positions = computeAgenticWorkflowLayout(nodes, edges)

    expect(positions.get('left')!.x).toBe(positions.get('right')!.x)
    expect(positions.get('left')!.y).not.toBe(positions.get('right')!.y)
  })

  it('returns an empty map for an empty node list without throwing', () => {
    expect(computeAgenticWorkflowLayout([], []).size).toBe(0)
  })

  // Regression test for a real bug: the old hand-rolled longest-path
  // relaxation algorithm had no cycle handling. A cycle (b <-> c below,
  // mirroring the real HUM-01 <-> HUM-02 escalation loop) made its rank
  // blow up to 94 for a 16-node graph that should have been ~8 ranks deep,
  // stretching a couple of edges across an enormous empty gap on screen.
  // dagre breaks cycles properly before ranking, so every node's rank here
  // must stay bounded by the actual node count, not run away.
  it('keeps ranks bounded when the graph contains a real cycle, not runaway', () => {
    const nodes = [agenticNode('a'), agenticNode('b'), agenticNode('c'), agenticNode('d')]
    const edges = [
      agenticEdge('a', 'b'),
      agenticEdge('b', 'c'),
      agenticEdge('c', 'b'), // the cycle: b <-> c
      agenticEdge('c', 'd'),
    ]
    const positions = computeAgenticWorkflowLayout(nodes, edges)

    const xs = nodes.map((n) => positions.get(n.id)!.x)
    const spread = Math.max(...xs) - Math.min(...xs)
    // With only 4 nodes, a sane layout spans at most ~4 ranks worth of
    // horizontal distance (a few hundred px) — the old bug would have
    // produced a spread orders of magnitude larger than the node count
    // could justify. This is the actual regression check: bounded by node
    // count, not by a specific pixel value that would make the test brittle.
    expect(spread).toBeLessThan(nodes.length * 400)
  })
})
