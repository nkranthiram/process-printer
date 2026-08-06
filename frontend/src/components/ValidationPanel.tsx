import type { ProcessTask, ValidationCase } from '../api'

interface Props {
  cases: ValidationCase[]
  tasks: ProcessTask[]
}

export default function ValidationPanel({ cases, tasks }: Props) {
  const titleById = new Map(tasks.map((t) => [t.id, t.title]))

  if (cases.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-slate-400">
        No traced scenarios recorded for this process map yet.
      </div>
    )
  }

  const passCount = cases.filter((c) => c.result === 'pass').length

  return (
    <div className="h-full overflow-y-auto px-6 py-6" data-testid="validation-panel">
      <p className="mb-4 text-xs text-slate-400">
        Real claim scenarios traced through the map by hand, checked against the
        PDS — {passCount}/{cases.length} passing.
      </p>
      <ul className="space-y-3">
        {cases.map((c) => (
          <li key={c.id} className="rounded-xl border border-slate-200 bg-white px-4 py-3.5 shadow-sm" data-testid="validation-case">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-medium text-slate-800">{c.scenario_name}</h3>
              <span
                className={[
                  'shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                  c.result === 'pass' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700',
                ].join(' ')}
              >
                {c.result}
              </span>
            </div>
            <p className="mt-1.5 text-xs text-slate-500">{c.claim_description}</p>
            <p className="mt-2 text-xs text-slate-600">
              <span className="text-slate-400">Expected: </span>
              {c.expected_outcome}
            </p>
            <p className="mt-1 text-[11px] text-slate-400">
              Path: {c.traced_path.map((id) => titleById.get(id) ?? id).join(' → ')}
            </p>
          </li>
        ))}
      </ul>
    </div>
  )
}
