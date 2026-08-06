"""Pydantic response models for the API layer. Kept separate from the SQLAlchemy
models (app/models/) deliberately — the DB schema and the wire schema are allowed
to diverge (e.g. resolving claim_refs from JSON ids into full citation objects)."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    filename: str
    title: str
    page_count: int
    status: str
    uploaded_at: dt.datetime

    class Config:
        from_attributes = True


class CitationOut(BaseModel):
    claim_id: str
    claim_type: str
    subject: str
    modality: str
    statement: str
    raw_quote: str
    page: int
    section_path: str | None
    extraction_confidence: float
    extractor_version: str


class TaskOut(BaseModel):
    id: str
    node_type: str
    title: str
    description: str
    position_x: float
    position_y: float
    citations: list[CitationOut]


class EdgeOut(BaseModel):
    id: str
    from_task_id: str
    to_task_id: str
    condition_label: str | None


class ProcessMapOut(BaseModel):
    id: str
    document_id: str
    version_label: str
    status: str
    tasks: list[TaskOut]
    edges: list[EdgeOut]


class IssueOut(BaseModel):
    id: str
    issue_type: str
    title: str
    description: str
    status: str
    process_task_id: str | None
    claim_refs: list[CitationOut]
    bpa_feedback: str | None = None
    resolution_notes: str | None = None


class IssueFeedbackIn(BaseModel):
    bpa_feedback: str | None = None
    status: str | None = None  # open | pending_review | resolved | deferred
    resolution_notes: str | None = None


class ValidationCaseOut(BaseModel):
    id: str
    scenario_name: str
    claim_description: str
    expected_outcome: str
    actual_outcome: str
    traced_path: list[str]
    result: str
    notes: str | None


class ChatRequest(BaseModel):
    message: str
    document_id: str


class ChatSource(BaseModel):
    task_id: str | None
    task_title: str | None
    claim_id: str | None
    subject: str | None
    page: int | None
    raw_quote: str | None


class ChatResponse(BaseModel):
    answer: str
    mode: str  # retrieval_only | llm_grounded | out_of_scope | change_request_logged
    sources: list[ChatSource]
    change_request_id: str | None = None


class ChangeRequestOut(BaseModel):
    id: str
    document_id: str
    source: str
    request_text: str
    change_type: str
    proposed_change: dict
    rationale: str | None
    status: str
    decision_notes: str | None
    resulting_process_map_id: str | None
    created_at: dt.datetime
    decided_at: dt.datetime | None


class ChangeRequestDecisionIn(BaseModel):
    decision_notes: str | None = None


class ProcessMapVersionOut(BaseModel):
    id: str
    version_label: str
    status: str
    change_summary: str | None
    changed_by: str | None
    created_at: dt.datetime
    is_current: bool
