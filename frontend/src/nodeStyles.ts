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

// Light-theme node styling: opaque pastel surfaces (not translucent overlays,
// which need a dark backdrop to read well) with a readable darker accent text
// and a saturated dot for quick visual scanning.
export const NODE_TYPE_STYLE: Record<NodeType, { accent: string; bg: string; border: string; dot: string }> = {
  input_required: { accent: 'text-sky-700', bg: 'bg-sky-50', border: 'border-sky-200', dot: 'bg-sky-500' },
  eligibility_test: { accent: 'text-violet-700', bg: 'bg-violet-50', border: 'border-violet-200', dot: 'bg-violet-500' },
  exclusion_test: { accent: 'text-rose-700', bg: 'bg-rose-50', border: 'border-rose-200', dot: 'bg-rose-500' },
  exception_test: { accent: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', dot: 'bg-amber-500' },
  evidence_sufficiency_test: { accent: 'text-teal-700', bg: 'bg-teal-50', border: 'border-teal-200', dot: 'bg-teal-500' },
  classification: { accent: 'text-indigo-700', bg: 'bg-indigo-50', border: 'border-indigo-200', dot: 'bg-indigo-500' },
  human_review: { accent: 'text-orange-700', bg: 'bg-orange-50', border: 'border-orange-200', dot: 'bg-orange-500' },
  decision: { accent: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-200', dot: 'bg-emerald-500' },
}

export const ISSUE_TYPE_LABEL: Record<string, string> = {
  gap: 'Gap',
  ambiguity: 'Ambiguity',
  low_confidence_extraction: 'Low confidence',
}

export const ISSUE_TYPE_STYLE: Record<string, { accent: string; bg: string; border: string }> = {
  gap: { accent: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200' },
  ambiguity: { accent: 'text-fuchsia-700', bg: 'bg-fuchsia-50', border: 'border-fuchsia-200' },
  low_confidence_extraction: { accent: 'text-rose-700', bg: 'bg-rose-50', border: 'border-rose-200' },
}

export const ISSUE_STATUS_LABEL: Record<string, string> = {
  open: 'Open',
  pending_review: 'Pending review',
  resolved: 'Resolved',
  deferred: 'Deferred',
}

export const ISSUE_STATUS_STYLE: Record<string, { accent: string; bg: string; border: string }> = {
  open: { accent: 'text-slate-600', bg: 'bg-slate-100', border: 'border-slate-300' },
  pending_review: { accent: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-200' },
  resolved: { accent: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-200' },
  deferred: { accent: 'text-slate-500', bg: 'bg-slate-50', border: 'border-slate-200' },
}

export const CHANGE_REQUEST_STATUS_STYLE: Record<string, { accent: string; bg: string; border: string }> = {
  pending: { accent: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-200' },
  approved: { accent: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-200' },
  rejected: { accent: 'text-slate-500', bg: 'bg-slate-50', border: 'border-slate-200' },
  apply_failed: { accent: 'text-rose-700', bg: 'bg-rose-50', border: 'border-rose-200' },
}
