import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ValidationPanel from './ValidationPanel'
import type { ProcessTask, ValidationCase } from '../api'

const tasks: ProcessTask[] = [
  { id: 't1', node_type: 'input_required', title: 'Capture the claim description', description: '', position_x: 0, position_y: 0, citations: [] },
  { id: 't10', node_type: 'decision', title: 'Reach the coverage decision', description: '', position_x: 0, position_y: 0, citations: [] },
]

const cases: ValidationCase[] = [
  {
    id: 'v1', scenario_name: 'Windscreen chip', claim_description: 'desc',
    expected_outcome: 'Covered', actual_outcome: 'Covered',
    traced_path: ['t1', 't10'], result: 'pass', notes: null,
  },
  {
    id: 'v2', scenario_name: 'Drunk driving crash', claim_description: 'desc2',
    expected_outcome: 'Not covered', actual_outcome: 'Not covered',
    traced_path: ['t10'], result: 'fail', notes: 'demo failing case',
  },
]

describe('ValidationPanel', () => {
  it('shows an empty state with no cases', () => {
    render(<ValidationPanel cases={[]} tasks={tasks} />)
    expect(screen.getByText(/no traced scenarios/i)).toBeInTheDocument()
  })

  it('renders every case with its pass/fail badge and resolves path task titles', () => {
    render(<ValidationPanel cases={cases} tasks={tasks} />)
    const items = screen.getAllByTestId('validation-case')
    expect(items).toHaveLength(2)
    expect(screen.getByText('pass')).toBeInTheDocument()
    expect(screen.getByText('fail')).toBeInTheDocument()
    expect(screen.getByText(/capture the claim description → reach the coverage decision/i)).toBeInTheDocument()
  })

  it('shows the pass/total summary count', () => {
    render(<ValidationPanel cases={cases} tasks={tasks} />)
    expect(screen.getByText(/1\/2 passing/i)).toBeInTheDocument()
  })
})
