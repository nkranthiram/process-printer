export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8811'

export interface DocumentSummary {
  id: string
  filename: string
  title: string
  page_count: number
  status: string
  uploaded_at: string
}

export interface Citation {
  claim_id: string
  claim_type: string
  subject: string
  modality: string
  statement: string
  raw_quote: string
  page: number
  section_path: string | null
  extraction_confidence: number
  extractor_version: string
}

export type NodeType =
  | 'input_required'
  | 'eligibility_test'
  | 'exclusion_test'
  | 'exception_test'
  | 'evidence_sufficiency_test'
  | 'classification'
  | 'human_review'
  | 'decision'

export interface ProcessTask {
  id: string
  node_type: NodeType
  title: string
  description: string
  position_x: number
  position_y: number
  citations: Citation[]
}

export interface ProcessEdge {
  id: string
  from_task_id: string
  to_task_id: string
  condition_label: string | null
}

export interface ProcessMap {
  id: string
  document_id: string
  version_label: string
  status: string
  tasks: ProcessTask[]
  edges: ProcessEdge[]
}

export interface Issue {
  id: string
  issue_type: 'gap' | 'ambiguity' | 'low_confidence_extraction'
  title: string
  description: string
  status: 'open' | 'pending_review' | 'resolved' | 'deferred'
  process_task_id: string | null
  claim_refs: Citation[]
  bpa_feedback: string | null
  resolution_notes: string | null
}

export interface ChangeRequest {
  id: string
  document_id: string
  source: string
  request_text: string
  change_type: 'add_task' | 'remove_task' | 'modify_task' | 'modify_edge' | 'unclear'
  proposed_change: Record<string, unknown>
  rationale: string | null
  status: 'pending' | 'approved' | 'rejected' | 'apply_failed'
  decision_notes: string | null
  resulting_process_map_id: string | null
  created_at: string
  decided_at: string | null
}

export interface ProcessMapVersionSummary {
  id: string
  version_label: string
  status: string
  change_summary: string | null
  changed_by: string | null
  created_at: string
  is_current: boolean
}

export interface ChatSource {
  task_id: string | null
  task_title: string | null
  claim_id: string | null
  subject: string | null
  page: number | null
  raw_quote: string | null
}

export interface ChatResponse {
  answer: string
  mode: 'retrieval_only' | 'llm_grounded' | 'out_of_scope' | 'change_request_logged'
  sources: ChatSource[]
  change_request_id: string | null
}

export interface ValidationCase {
  id: string
  scenario_name: string
  claim_description: string
  expected_outcome: string
  actual_outcome: string
  traced_path: string[]
  result: 'pass' | 'fail'
  notes: string | null
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status} ${await res.text()}`)
  }
  return res.json()
}

export function listDocuments(): Promise<DocumentSummary[]> {
  return getJSON('/api/documents')
}

export function getProcessMap(documentId: string): Promise<ProcessMap> {
  return getJSON(`/api/documents/${documentId}/process-map`)
}

export function listIssues(documentId: string): Promise<Issue[]> {
  return getJSON(`/api/documents/${documentId}/issues`)
}

export function listValidationCases(documentId: string): Promise<ValidationCase[]> {
  return getJSON(`/api/documents/${documentId}/validation-cases`)
}

export async function sendChat(documentId: string, message: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId, message }),
  })
  if (!res.ok) {
    throw new Error(`POST /api/chat failed: ${res.status} ${await res.text()}`)
  }
  return res.json()
}

export function listChangeRequests(documentId: string): Promise<ChangeRequest[]> {
  return getJSON(`/api/documents/${documentId}/change-requests`)
}

export function listProcessMapVersions(documentId: string): Promise<ProcessMapVersionSummary[]> {
  return getJSON(`/api/documents/${documentId}/process-map/versions`)
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(`POST ${path} failed: ${res.status} ${await res.text()}`)
  }
  return res.json()
}

export function approveChangeRequest(documentId: string, crId: string, decisionNotes?: string): Promise<ChangeRequest> {
  return postJSON(`/api/documents/${documentId}/change-requests/${crId}/approve`, { decision_notes: decisionNotes ?? null })
}

export function rejectChangeRequest(documentId: string, crId: string, decisionNotes?: string): Promise<ChangeRequest> {
  return postJSON(`/api/documents/${documentId}/change-requests/${crId}/reject`, { decision_notes: decisionNotes ?? null })
}

export async function updateIssueFeedback(
  documentId: string,
  issueId: string,
  body: { bpa_feedback?: string; status?: string; resolution_notes?: string },
): Promise<Issue> {
  const res = await fetch(`${API_BASE}/api/documents/${documentId}/issues/${issueId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(`PATCH issue failed: ${res.status} ${await res.text()}`)
  }
  return res.json()
}
