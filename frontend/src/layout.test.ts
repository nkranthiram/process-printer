import { describe, expect, it } from 'vitest'
import { computeLayeredLayout } from './layout'
import type { ProcessEdge, ProcessTask } from './api'

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

describe('computeLayeredLayout', () => {
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

  it('a node with two incoming edges from different ranks sits below BOTH predecessors (longest-path rank)', () => {
    // a -> b -> d, a -> d  (d has two parents at different depths)
    const tasks = [task('a'), task('b'), task('d')]
    const edges = [edge('a', 'b'), edge('b', 'd'), edge('a', 'd')]
    const positions = computeLayeredLayout(tasks, edges)

    expect(positions.get('d')!.y).toBeGreaterThan(positions.get('a')!.y)
    expect(positions.get('d')!.y).toBeGreaterThan(positions.get('b')!.y)
  })

  it('no two nodes ever land on the exact same (x, y) — the concrete overlap bug being fixed', () => {
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
