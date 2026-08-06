from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.chat import answer_question
from app.database import get_db
from app.models.claim import AtomicClaim
from app.models.document import DocumentVersion
from app.models.issue import Issue
from app.models.process_map import ProcessEdge, ProcessMapVersion, ProcessTask
from app.models.validation import ValidationCase
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ChatSource,
    CitationOut,
    DocumentOut,
    EdgeOut,
    IssueOut,
    ProcessMapOut,
    TaskOut,
    ValidationCaseOut,
)

router = APIRouter(prefix="/api")


def _citation_from_claim(claim: AtomicClaim) -> CitationOut:
    return CitationOut(
        claim_id=claim.id,
        claim_type=claim.claim_type,
        subject=claim.subject,
        modality=claim.modality,
        statement=claim.statement,
        raw_quote=claim.raw_quote,
        page=claim.source_span.page,
        section_path=claim.source_span.section_path,
        extraction_confidence=claim.extraction_confidence,
        extractor_version=claim.extractor_version,
    )


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return db.query(DocumentVersion).order_by(DocumentVersion.uploaded_at.desc()).all()


@router.get("/documents/{document_id}/process-map", response_model=ProcessMapOut)
def get_process_map(document_id: str, db: Session = Depends(get_db)):
    pm = (
        db.query(ProcessMapVersion)
        .filter_by(document_id=document_id)
        .order_by(ProcessMapVersion.created_at.desc())
        .first()
    )
    if pm is None:
        raise HTTPException(404, f"No process map found for document {document_id}")

    claims_by_id = {c.id: c for c in db.query(AtomicClaim).filter_by(document_id=document_id).all()}

    tasks = db.query(ProcessTask).filter_by(process_map_id=pm.id).all()
    task_outs = []
    for t in tasks:
        claim_ids = json.loads(t.claim_refs or "[]")
        citations = [_citation_from_claim(claims_by_id[cid]) for cid in claim_ids if cid in claims_by_id]
        task_outs.append(TaskOut(
            id=t.id, node_type=t.node_type, title=t.title, description=t.description,
            position_x=t.position_x, position_y=t.position_y, citations=citations,
        ))

    edges = db.query(ProcessEdge).filter_by(process_map_id=pm.id).all()
    edge_outs = [
        EdgeOut(id=e.id, from_task_id=e.from_task_id, to_task_id=e.to_task_id, condition_label=e.condition_label)
        for e in edges
    ]

    return ProcessMapOut(
        id=pm.id, document_id=pm.document_id, version_label=pm.version_label,
        status=pm.status, tasks=task_outs, edges=edge_outs,
    )


@router.get("/documents/{document_id}/issues", response_model=list[IssueOut])
def list_issues(document_id: str, db: Session = Depends(get_db)):
    claims_by_id = {c.id: c for c in db.query(AtomicClaim).filter_by(document_id=document_id).all()}
    issues = db.query(Issue).filter_by(document_id=document_id).order_by(Issue.created_at).all()
    out = []
    for i in issues:
        claim_ids = json.loads(i.claim_refs or "[]")
        citations = [_citation_from_claim(claims_by_id[cid]) for cid in claim_ids if cid in claims_by_id]
        out.append(IssueOut(
            id=i.id, issue_type=i.issue_type, title=i.title, description=i.description,
            status=i.status, process_task_id=i.process_task_id, claim_refs=citations,
        ))
    return out


@router.get("/documents/{document_id}/validation-cases", response_model=list[ValidationCaseOut])
def list_validation_cases(document_id: str, db: Session = Depends(get_db)):
    pm = (
        db.query(ProcessMapVersion)
        .filter_by(document_id=document_id)
        .order_by(ProcessMapVersion.created_at.desc())
        .first()
    )
    if pm is None:
        raise HTTPException(404, f"No process map found for document {document_id}")

    cases = db.query(ValidationCase).filter_by(process_map_id=pm.id).order_by(ValidationCase.recorded_at).all()
    return [
        ValidationCaseOut(
            id=c.id, scenario_name=c.scenario_name, claim_description=c.claim_description,
            expected_outcome=c.expected_outcome, actual_outcome=c.actual_outcome,
            traced_path=json.loads(c.traced_path), result=c.result, notes=c.notes,
        )
        for c in cases
    ]


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    doc = db.query(DocumentVersion).filter_by(id=req.document_id).first()
    if doc is None:
        raise HTTPException(404, f"Unknown document_id {req.document_id}")

    answer, mode, retrieved = answer_question(db, req.document_id, req.message)

    sources: list[ChatSource] = []
    for r in retrieved:
        if not r.claims:
            sources.append(ChatSource(task_id=r.task.id, task_title=r.task.title, claim_id=None, subject=None, page=None, raw_quote=None))
        for c in r.claims:
            sources.append(ChatSource(
                task_id=r.task.id, task_title=r.task.title, claim_id=c.id,
                subject=c.subject, page=c.source_span.page, raw_quote=c.raw_quote,
            ))

    return ChatResponse(answer=answer, mode=mode, sources=sources)
