import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ChangeRequestsPanel from './ChangeRequestsPanel'
import type { ChangeRequest } from '../api'
import * as api from '../api'

const pending: ChangeRequest = {
  id: 'cr1', document_id: 'doc-1', source: 'chat',
  request_text: 'remove the additional covers step',
  change_type: 'remove_task', proposed_change: { task_id: 't9' },
  rationale: 'BPA said it was redundant', status: 'pending',
  decision_notes: null, resulting_process_map_id: null,
  created_at: '2026-08-06T00:00:00Z', decided_at: null,
}

const unclear: ChangeRequest = {
  ...pending, id: 'cr2', change_type: 'unclear', rationale: 'Could not parse',
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ChangeRequestsPanel', () => {
  it('shows an empty state with no change requests', () => {
    render(<ChangeRequestsPanel documentId="doc-1" changeRequests={[]} onDecided={() => {}} />)
    expect(screen.getByText(/no process-map change requests yet/i)).toBeInTheDocument()
  })

  it('renders a pending change request with approve/reject actions', () => {
    render(<ChangeRequestsPanel documentId="doc-1" changeRequests={[pending]} onDecided={() => {}} />)
    expect(screen.getByText(/remove the additional covers step/i)).toBeInTheDocument()
    expect(screen.getByTestId('approve-cr-cr1')).toBeInTheDocument()
    expect(screen.getByTestId('reject-cr-cr1')).toBeInTheDocument()
  })

  it('an "unclear" change request has no approve button, only a note', () => {
    render(<ChangeRequestsPanel documentId="doc-1" changeRequests={[unclear]} onDecided={() => {}} />)
    expect(screen.queryByTestId('approve-cr-cr2')).not.toBeInTheDocument()
    expect(screen.getByText(/couldn.t be turned into a structured edit/i)).toBeInTheDocument()
  })

  it('approving calls the API and reports the updated status via onDecided', async () => {
    const approved: ChangeRequest = { ...pending, status: 'approved', resulting_process_map_id: 'pm-2' }
    vi.spyOn(api, 'approveChangeRequest').mockResolvedValue(approved)
    const onDecided = vi.fn()

    render(<ChangeRequestsPanel documentId="doc-1" changeRequests={[pending]} onDecided={onDecided} />)
    fireEvent.click(screen.getByTestId('approve-cr-cr1'))

    await waitFor(() => expect(onDecided).toHaveBeenCalledWith(approved))
    expect(api.approveChangeRequest).toHaveBeenCalledWith('doc-1', 'cr1')
  })

  it('rejecting calls the API and reports the updated status via onDecided', async () => {
    const rejected: ChangeRequest = { ...pending, status: 'rejected' }
    vi.spyOn(api, 'rejectChangeRequest').mockResolvedValue(rejected)
    const onDecided = vi.fn()

    render(<ChangeRequestsPanel documentId="doc-1" changeRequests={[pending]} onDecided={onDecided} />)
    fireEvent.click(screen.getByTestId('reject-cr-cr1'))

    await waitFor(() => expect(onDecided).toHaveBeenCalledWith(rejected))
  })
})
