import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import IssuesPanel from './IssuesPanel'
import type { Issue, ProcessTask } from '../api'

const tasks: ProcessTask[] = [
  { id: 't1', node_type: 'exclusion_test', title: 'Check general exclusions', description: '', position_x: 0, position_y: 0, citations: [] },
]

const issues: Issue[] = [
  {
    id: 'i1',
    issue_type: 'gap',
    title: 'No claim-lodgement deadline found',
    description: 'The extracted sections do not state a deadline.',
    status: 'open',
    process_task_id: 't1',
    claim_refs: [],
  },
  {
    id: 'i2',
    issue_type: 'ambiguity',
    title: '"Reasonable distance" is undefined',
    description: 'The PDS does not define reasonable distance.',
    status: 'open',
    process_task_id: null,
    claim_refs: [],
  },
]

describe('IssuesPanel', () => {
  it('shows an empty state when there are no issues', () => {
    render(<IssuesPanel issues={[]} tasks={tasks} />)
    expect(screen.getByText(/no open gaps or ambiguities/i)).toBeInTheDocument()
  })

  it('renders every issue with its type label and title', () => {
    render(<IssuesPanel issues={issues} tasks={tasks} />)
    const items = screen.getAllByTestId('issue-item')
    expect(items).toHaveLength(2)
    expect(screen.getByText('Gap')).toBeInTheDocument()
    expect(screen.getByText('Ambiguity')).toBeInTheDocument()
    expect(screen.getByText(/no claim-lodgement deadline found/i)).toBeInTheDocument()
  })

  it('links an issue to its task title when process_task_id is set', () => {
    render(<IssuesPanel issues={issues} tasks={tasks} />)
    expect(screen.getByText(/check general exclusions/i)).toBeInTheDocument()
  })
})
