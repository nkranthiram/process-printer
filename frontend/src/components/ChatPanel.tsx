import { useState, type FormEvent } from 'react'
import { sendChat, consolidateReviewSession, type ChatResponse, type ReviewSession, type TranscriptTurn } from '../api'
import ReviewSessionPanel from './ReviewSessionPanel'

interface Props {
  documentId: string
  onChangesApplied: () => void
}

interface Turn {
  role: 'user' | 'assistant'
  text: string
  response?: ChatResponse
}

const MODE_LABEL: Record<string, { label: string; className: string }> = {
  retrieval_only: { label: 'Retrieval-only (no LLM key configured)', className: 'text-slate-400' },
  llm_grounded: { label: 'LLM-grounded', className: 'text-slate-400' },
  out_of_scope: { label: 'Out of scope for this tool', className: 'text-amber-600' },
  change_request_logged: { label: 'Logged as a pending change request', className: 'text-blue-600 font-medium' },
}

export default function ChatPanel({ documentId, onChangesApplied }: Props) {
  const [input, setInput] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [consolidating, setConsolidating] = useState(false)
  const [reviewSession, setReviewSession] = useState<ReviewSession | null>(null)
  const [reviewError, setReviewError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const message = input.trim()
    if (!message || loading) return

    setTurns((t) => [...t, { role: 'user', text: message }])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const response = await sendChat(documentId, message)
      setTurns((t) => [...t, { role: 'assistant', text: response.answer, response }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong asking the chatbot.')
    } finally {
      setLoading(false)
    }
  }

  async function handleReviewAndApply() {
    if (turns.length === 0) return
    setConsolidating(true)
    setReviewError(null)
    try {
      const transcript: TranscriptTurn[] = turns.map((t, i) => ({ role: t.role, text: t.text, ref: `turn-${i + 1}` }))
      const session = await consolidateReviewSession(documentId, transcript)
      setReviewSession(session)
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : 'Failed to consolidate the conversation.')
    } finally {
      setConsolidating(false)
    }
  }

  return (
    <div className="flex h-full flex-col" data-testid="chat-panel">
      <div className="border-b border-slate-100 bg-blue-50/60 px-5 py-3">
        <p className="text-xs text-blue-900">
          This chat is for reviewing and giving feedback on the <strong>process map</strong> —
          ask why a step is there, or say what you&rsquo;d like added, removed, or
          changed. It won&rsquo;t answer coverage questions; that&rsquo;s not what this tool is for.
        </p>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
        {turns.length === 0 && (
          <p className="text-sm text-slate-400">
            Try &ldquo;Why is the exclusions check before the excess step?&rdquo; or
            &ldquo;Add a step to verify the incident date.&rdquo;
          </p>
        )}
        {turns.map((turn, i) => (
          <div key={i} className={turn.role === 'user' ? 'text-right' : 'text-left'}>
            <div
              className={[
                'inline-block max-w-[90%] rounded-2xl px-3.5 py-2 text-sm whitespace-pre-line text-left',
                turn.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-700 shadow-sm',
              ].join(' ')}
            >
              {turn.text}
            </div>
            {turn.response && turn.response.sources.length > 0 && (
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {turn.response.sources
                  .filter((s) => s.claim_id)
                  .slice(0, 5)
                  .map((s) => (
                    <span
                      key={s.claim_id}
                      title={s.raw_quote ?? ''}
                      className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] text-slate-500"
                    >
                      p.{s.page} · {s.subject}
                    </span>
                  ))}
              </div>
            )}
            {turn.response && (
              <div className={`mt-1 text-[10px] ${MODE_LABEL[turn.response.mode]?.className ?? 'text-slate-400'}`}>
                {MODE_LABEL[turn.response.mode]?.label ?? turn.response.mode}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="text-xs text-slate-400">Thinking…</div>}
        {error && <div className="text-xs text-rose-600">{error}</div>}
      </div>

      <div className="border-t border-slate-100 px-5 py-2.5">
        {reviewError && <p className="mb-2 text-xs text-rose-600">{reviewError}</p>}
        <button
          type="button"
          disabled={turns.length === 0 || consolidating}
          onClick={handleReviewAndApply}
          data-testid="review-and-apply-button"
          className="w-full rounded-xl border border-blue-200 bg-blue-50 px-3.5 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {consolidating ? 'Consolidating this conversation…' : 'Review & Apply Changes'}
        </button>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-slate-100 p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a step, or propose a change…"
          className="flex-1 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:border-blue-400 focus:outline-none"
          data-testid="chat-input"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
        >
          Send
        </button>
      </form>

      {reviewSession && (
        <ReviewSessionPanel
          documentId={documentId}
          session={reviewSession}
          onSessionChanged={setReviewSession}
          onApplied={onChangesApplied}
          onClose={() => setReviewSession(null)}
        />
      )}
    </div>
  )
}
