import type { ProcessTask, ValidationCase } from '../api'

interface Props {
  cases: ValidationCase[]
  tasks: ProcessTask[]
}

export default function ValidationPanel({ cases, tasks }: Props) {
  const titleById = new Map(tasks.map((t) => [t.id, t.title]))

  if (cases.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-slate-500">
        No traced scenarios recorded for this process map yet.
      </div>
    )
  }

  const passCount = cases.filter((c) => c.result === 'pass').length

  return (
    <div className="h-full overflow-y-auto px-5 py-5" data-testid="validation-panel">
      <p className="mb-4 text-xs text-slate-500">
        Real claim scenarios traced through the map by hand, checked against the
        PDS — {passCount}/{cases.length} passing.
      </p>
      <ul className="space-y-3">
        {cases.map((c) => (
          <li key={c.id} className="rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-3" data-testid="validation-case">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-medium text-slate-100">{c.scenario_name}</h3>
              <span
                className={[
                  'shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                  c.result === 'pass' ? 'bg-emerald-500/15 text-emerald-300' : 'bg-rose-500/15 text-rose-300',
                ].join(' ')}
              >
                {c.result}
              </span>
            </div>
            <p className="mt-1.5 text-xs text-slate-400">{c.claim_description}</p>
            <p className="mt-2 text-xs text-slate-300">
              <span className="text-slate-500">Expected: </span>
              {c.expected_outcome}
            </p>
            <p className="mt-1 text-[11px] text-slate-500">
              Path: {c.traced_path.map((id) => titleById.get(id) ?? id).join(' → ')}
            </p>
          </li>
        ))}
      </ul>
    </div>
  )
}
