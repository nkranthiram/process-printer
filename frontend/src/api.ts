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
  status: string
  process_task_id: string | null
  claim_refs: Citation[]
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
  mode: 'retrieval_only' | 'llm_grounded'
  sources: ChatSource[]
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
