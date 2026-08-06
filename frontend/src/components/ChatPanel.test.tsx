import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
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

    render(<ChatPanel documentId="doc-1" />)

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

    render(<ChatPanel documentId="doc-1" />)
    fireEvent.change(screen.getByTestId('chat-input'), { target: { value: 'anything' } })
    fireEvent.click(screen.getByRole('button', { name: /send/i }))

    await waitFor(() => expect(screen.getByText(/network down/i)).toBeInTheDocument())
  })

  it('does not send an empty message', () => {
    const sendChatSpy = vi.spyOn(api, 'sendChat')
    render(<ChatPanel documentId="doc-1" />)
    fireEvent.click(screen.getByRole('button', { name: /send/i }))
    expect(sendChatSpy).not.toHaveBeenCalled()
  })
})
