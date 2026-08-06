import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import ChatPanel from './ChatPanel'
import * as api from '../api'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ChatPanel', () => {
  it('sends the typed message and renders the assistant reply with its sources', async () => {
    const sendChatSpy = vi.spyOn(api, 'sendChat').mockResolvedValue({
      answer: 'Windscreen claims are excess-free unless a full replacement is needed twice.',
      mode: 'retrieval_only',
      sources: [
        { task_id: 't5', task_title: 'Check cover-specific conditions', claim_id: 'c9', subject: 'windscreen_cover', page: 42, raw_quote: 'quote text' },
      ],
      change_request_id: null,
    })

    render(<ChatPanel documentId="doc-1" onChangesApplied={() => {}} />)

    fireEvent.change(screen.getByTestId('chat-input'), { target: { value: 'Is a cracked windscreen covered?' } })
    fireEvent.click(screen.getByRole('button', { name: /send/i }))

    // User's own message renders immediately, before the network call resolves.
    expect(screen.getByText('Is a cracked windscreen covered?')).toBeInTheDocument()

    await waitFor(() => expect(screen.getByText(/windscreen claims are excess-free/i)).toBeInTheDocument())

    expect(sendChatSpy).toHaveBeenCalledWith('doc-1', 'Is a cracked windscreen covered?')
    expect(screen.getByText(/p\.42 · windscreen_cover/i)).toBeInTheDocument()
    expect(screen.getByText(/retrieval-only/i)).toBeInTheDocument()
  })

  it('shows an error message if the request fails, rather than failing silently', async () => {
    vi.spyOn(api, 'sendChat').mockRejectedValue(new Error('network down'))

    render(<ChatPanel documentId="doc-1" onChangesApplied={() => {}} />)
    fireEvent.change(screen.getByTestId('chat-input'), { target: { value: 'anything' } })
    fireEvent.click(screen.getByRole('button', { name: /send/i }))

    await waitFor(() => expect(screen.getByText(/network down/i)).toBeInTheDocument())
  })

  it('does not send an empty message', () => {
    const sendChatSpy = vi.spyOn(api, 'sendChat')
    render(<ChatPanel documentId="doc-1" onChangesApplied={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /send/i }))
    expect(sendChatSpy).not.toHaveBeenCalled()
  })

  it('the Review & Apply Changes button is disabled until there is at least one turn', () => {
    render(<ChatPanel documentId="doc-1" onChangesApplied={() => {}} />)
    expect(screen.getByTestId('review-and-apply-button')).toBeDisabled()
  })

  it('clicking Review & Apply Changes consolidates the transcript and opens the review panel', async () => {
    vi.spyOn(api, 'sendChat').mockResolvedValue({
      answer: 'Noted.', mode: 'change_request_logged', sources: [], change_request_id: null,
    })
    const consolidateSpy = vi.spyOn(api, 'consolidateReviewSession').mockResolvedValue({
      id: 's1', document_id: 'doc-1', base_process_map_id: 'pm-1', status: 'reconciled',
      created_at: '2026-08-06T00:00:00Z', confirmed_at: null, resulting_process_map_id: null,
      items: [{
        id: 'di1', session_id: 's1', change_type: 'remove_task', proposed_change: { task_id: 't9' },
        rationale: 'redundant', source_message_refs: ['turn-1'], status: 'draft',
        superseded_by_item_id: null, human_override: false,
        created_at: '2026-08-06T00:00:00Z', updated_at: '2026-08-06T00:00:00Z',
      }],
    })

    render(<ChatPanel documentId="doc-1" onChangesApplied={() => {}} />)
    fireEvent.change(screen.getByTestId('chat-input'), { target: { value: 'remove the redundant step' } })
    fireEvent.click(screen.getByRole('button', { name: /send/i }))
    await waitFor(() => expect(screen.getByText('Noted.')).toBeInTheDocument())

    expect(screen.getByTestId('review-and-apply-button')).not.toBeDisabled()
    fireEvent.click(screen.getByTestId('review-and-apply-button'))

    await waitFor(() => expect(screen.getByTestId('review-session-panel')).toBeInTheDocument())
    expect(consolidateSpy).toHaveBeenCalledWith('doc-1', [
      { role: 'user', text: 'remove the redundant step', ref: 'turn-1' },
      { role: 'assistant', text: 'Noted.', ref: 'turn-2' },
    ])
    const panel = screen.getByTestId('review-session-panel')
    expect(within(panel).getByText(/redundant/i)).toBeInTheDocument()
  })
})
