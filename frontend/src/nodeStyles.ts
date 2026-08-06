import type { NodeType } from './api'

export const NODE_TYPE_LABEL: Record<NodeType, string> = {
  input_required: 'Input',
  eligibility_test: 'Eligibility check',
  exclusion_test: 'Exclusion check',
  exception_test: 'Exception check',
  evidence_sufficiency_test: 'Evidence check',
  classification: 'Classification',
  human_review: 'Human review',
  decision: 'Decision',
}

export const NODE_TYPE_STYLE: Record<NodeType, { accent: string; bg: string; border: string; dot: string }> = {
  input_required: { accent: 'text-sky-300', bg: 'bg-sky-500/10', border: 'border-sky-500/40', dot: 'bg-sky-400' },
  eligibility_test: { accent: 'text-violet-300', bg: 'bg-violet-500/10', border: 'border-violet-500/40', dot: 'bg-violet-400' },
  exclusion_test: { accent: 'text-rose-300', bg: 'bg-rose-500/10', border: 'border-rose-500/40', dot: 'bg-rose-400' },
  exception_test: { accent: 'text-amber-300', bg: 'bg-amber-500/10', border: 'border-amber-500/40', dot: 'bg-amber-400' },
  evidence_sufficiency_test: { accent: 'text-teal-300', bg: 'bg-teal-500/10', border: 'border-teal-500/40', dot: 'bg-teal-400' },
  classification: { accent: 'text-indigo-300', bg: 'bg-indigo-500/10', border: 'border-indigo-500/40', dot: 'bg-indigo-400' },
  human_review: { accent: 'text-orange-300', bg: 'bg-orange-500/10', border: 'border-orange-500/40', dot: 'bg-orange-400' },
  decision: { accent: 'text-emerald-300', bg: 'bg-emerald-500/10', border: 'border-emerald-500/40', dot: 'bg-emerald-400' },
}

export const ISSUE_TYPE_LABEL: Record<string, string> = {
  gap: 'Gap',
  ambiguity: 'Ambiguity',
  low_confidence_extraction: 'Low confidence',
}

export const ISSUE_TYPE_STYLE: Record<string, { accent: string; bg: string; border: string }> = {
  gap: { accent: 'text-amber-300', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
  ambiguity: { accent: 'text-fuchsia-300', bg: 'bg-fuchsia-500/10', border: 'border-fuchsia-500/30' },
  low_confidence_extraction: { accent: 'text-rose-300', bg: 'bg-rose-500/10', border: 'border-rose-500/30' },
}
