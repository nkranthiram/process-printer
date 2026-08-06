import { useState, type FormEvent } from 'react'
import { sendChat, type ChatResponse } from '../api'

interface Props {
  documentId: string
}

interface Turn {
  role: 'user' | 'assistant'
  text: string
  response?: ChatResponse
}

export default function ChatPanel({ documentId }: Props) {
  const [input, setInput] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  return (
    <div className="flex h-full flex-col" data-testid="chat-panel">
      <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
        {turns.length === 0 && (
          <p className="text-sm text-slate-500">
            Ask about the process — e.g. &ldquo;Is a cracked windscreen covered?&rdquo; or
            &ldquo;What excess applies if I wasn&rsquo;t at fault?&rdquo;
          </p>
        )}
        {turns.map((turn, i) => (
          <div key={i} className={turn.role === 'user' ? 'text-right' : 'text-left'}>
            <div
              className={[
                'inline-block max-w-[90%] rounded-xl px-3 py-2 text-sm whitespace-pre-line text-left',
                turn.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-200',
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
                      className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[10px] text-slate-400"
                    >
                      p.{s.page} · {s.subject}
                    </span>
                  ))}
              </div>
            )}
            {turn.response && (
              <div className="mt-1 text-[10px] text-slate-600">
                {turn.response.mode === 'retrieval_only' ? 'Retrieval-only (no LLM key configured)' : 'LLM-grounded'}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="text-xs text-slate-500">Thinking…</div>}
        {error && <div className="text-xs text-rose-400">{error}</div>}
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-slate-800 p-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about this process…"
          className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-indigo-500 focus:outline-none"
          data-testid="chat-input"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  )
}
