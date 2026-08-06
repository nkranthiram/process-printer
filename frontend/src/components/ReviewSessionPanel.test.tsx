import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ReviewSessionPanel from './ReviewSessionPanel'
import type { ConfirmResult, DraftChangeItem, ReviewSession } from '../api'
import * as api from '../api'

const draftItem: DraftChangeItem = {
  id: 'di1', session_id: 's1', change_type: 'remove_task',
  proposed_change: { task_id: 't9' }, rationale: 'BPA said redundant',
  source_message_refs: ['turn-1'], status: 'draft', superseded_by_item_id: null,
  human_override: false, created_at: '2026-08-06T00:00:00Z', updated_at: '2026-08-06T00:00:00Z',
}

const session: ReviewSession = {
  id: 's1', document_id: 'doc-1', base_process_map_id: 'pm-1', status: 'reconciled',
  created_at: '2026-08-06T00:00:00Z', confirmed_at: null, resulting_process_map_id: null,
  items: [draftItem],
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ReviewSessionPanel', () => {
  it('renders draft items with approve/reject/edit actions', () => {
    render(<ReviewSessionPanel documentId="doc-1" session={session} onSessionChanged={() => {}} onApplied={() => {}} onClose={() => {}} />)
    expect(screen.getByText(/BPA said redundant/i)).toBeInTheDocument()
    expect(screen.getByTestId('approve-item-di1')).toBeInTheDocument()
    expect(screen.getByTestId('reject-item-di1')).toBeInTheDocument()
  })

  it('approving an item calls the API and updates via onSessionChanged', async () => {
    const approved: DraftChangeItem = { ...draftItem, status: 'approved' }
    vi.spyOn(api, 'updateDraftItem').mockResolvedValue(approved)
    const onSessionChanged = vi.fn()

    render(<ReviewSessionPanel documentId="doc-1" session={session} onSessionChanged={onSessionChanged} onApplied={() => {}} onClose={() => {}} />)
    fireEvent.click(screen.getByTestId('approve-item-di1'))

    await waitFor(() => expect(onSessionChanged).toHaveBeenCalled())
    expect(api.updateDraftItem).toHaveBeenCalledWith('doc-1', 's1', 'di1', { status: 'approved' })
  })

  it('confirm button is disabled until at least one item is approved', () => {
    render(<ReviewSessionPanel documentId="doc-1" session={session} onSessionChanged={() => {}} onApplied={() => {}} onClose={() => {}} />)
    expect(screen.getByTestId('confirm-review-session')).toBeDisabled()
  })

  it('confirming applies the session and calls onApplied + onClose on success', async () => {
    const approvedSession: ReviewSession = { ...session, items: [{ ...draftItem, status: 'approved' }] }
    const result: ConfirmResult = {
      success: true,
      new_version: { id: 'pm-2', version_label: 'v2', status: 'draft', change_summary: 'x', changed_by: 'bpa', created_at: '2026-08-06T00:00:00Z', is_current: true },
      change_summaries: ['Removed step'],
      failed_item_id: null, error: null,
    }
    vi.spyOn(api, 'confirmReviewSession').mockResolvedValue(result)
    const onApplied = vi.fn()
    const onClose = vi.fn()
    const onSessionChanged = vi.fn()

    render(<ReviewSessionPanel documentId="doc-1" session={approvedSession} onSessionChanged={onSessionChanged} onApplied={onApplied} onClose={onClose} />)
    fireEvent.click(screen.getByTestId('confirm-review-session'))

    await waitFor(() => expect(onApplied).toHaveBeenCalled())
    expect(onClose).toHaveBeenCalled()
    expect(onSessionChanged).toHaveBeenCalledWith(null)
  })

  it('shows an error and flags the failing item if confirm fails', async () => {
    const approvedSession: ReviewSession = { ...session, items: [{ ...draftItem, status: 'approved' }] }
    const result: ConfirmResult = {
      success: false, new_version: null, change_summaries: [],
      failed_item_id: 'di1', error: 'task_id does not exist',
    }
    vi.spyOn(api, 'confirmReviewSession').mockResolvedValue(result)
    const onSessionChanged = vi.fn()

    render(<ReviewSessionPanel documentId="doc-1" session={approvedSession} onSessionChanged={onSessionChanged} onApplied={() => {}} onClose={() => {}} />)
    fireEvent.click(screen.getByTestId('confirm-review-session'))

    await waitFor(() => expect(screen.getByText(/task_id does not exist/i)).toBeInTheDocument())
    expect(onSessionChanged).toHaveBeenCalled()
  })
})
