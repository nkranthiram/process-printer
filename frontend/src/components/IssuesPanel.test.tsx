import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import IssuesPanel from './IssuesPanel'
import type { Issue, ProcessTask } from '../api'
import * as api from '../api'

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
    bpa_feedback: null,
    resolution_notes: null,
  },
  {
    id: 'i2',
    issue_type: 'ambiguity',
    title: '"Reasonable distance" is undefined',
    description: 'The PDS does not define reasonable distance.',
    status: 'open',
    process_task_id: null,
    claim_refs: [],
    bpa_feedback: null,
    resolution_notes: null,
  },
]

afterEach(() => {
  vi.restoreAllMocks()
})

describe('IssuesPanel', () => {
  it('shows an empty state when there are no issues', () => {
    render(<IssuesPanel issues={[]} tasks={tasks} documentId="doc-1" onIssueUpdated={() => {}} />)
    expect(screen.getByText(/no open gaps or ambiguities/i)).toBeInTheDocument()
  })

  it('renders every issue with its type label and title', () => {
    render(<IssuesPanel issues={issues} tasks={tasks} documentId="doc-1" onIssueUpdated={() => {}} />)
    const items = screen.getAllByTestId('issue-item')
    expect(items).toHaveLength(2)
    expect(screen.getByText('Gap')).toBeInTheDocument()
    expect(screen.getByText('Ambiguity')).toBeInTheDocument()
    expect(screen.getByText(/no claim-lodgement deadline found/i)).toBeInTheDocument()
  })

  it('links an issue to its task title when process_task_id is set', () => {
    render(<IssuesPanel issues={issues} tasks={tasks} documentId="doc-1" onIssueUpdated={() => {}} />)
    expect(screen.getByText(/check general exclusions/i)).toBeInTheDocument()
  })

  it('submits BPA feedback and calls onIssueUpdated with the server response', async () => {
    const updated: Issue = { ...issues[0], status: 'pending_review', bpa_feedback: 'Please confirm with legal.' }
    vi.spyOn(api, 'updateIssueFeedback').mockResolvedValue(updated)
    const onIssueUpdated = vi.fn()

    render(<IssuesPanel issues={issues} tasks={tasks} documentId="doc-1" onIssueUpdated={onIssueUpdated} />)

    fireEvent.change(screen.getByTestId('issue-feedback-input-i1'), { target: { value: 'Please confirm with legal.' } })
    fireEvent.click(screen.getByTestId('issue-feedback-submit-i1'))

    await waitFor(() => expect(onIssueUpdated).toHaveBeenCalledWith(updated))
    expect(api.updateIssueFeedback).toHaveBeenCalledWith('doc-1', 'i1', {
      bpa_feedback: 'Please confirm with legal.',
      status: 'pending_review',
    })
  })

  it('marking an issue resolved calls the API with status=resolved', async () => {
    const updated: Issue = { ...issues[0], status: 'resolved' }
    vi.spyOn(api, 'updateIssueFeedback').mockResolvedValue(updated)
    const onIssueUpdated = vi.fn()

    render(<IssuesPanel issues={issues} tasks={tasks} documentId="doc-1" onIssueUpdated={onIssueUpdated} />)
    fireEvent.click(screen.getByTestId('issue-resolve-i1'))

    await waitFor(() => expect(onIssueUpdated).toHaveBeenCalledWith(updated))
    expect(api.updateIssueFeedback).toHaveBeenCalledWith('doc-1', 'i1', { status: 'resolved' })
  })
})
