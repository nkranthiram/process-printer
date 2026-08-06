from __future__ import annotations

import datetime as dt
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.chat import handle_message
from app.database import get_db
from app.models.claim import AtomicClaim
from app.models.change_request import ChangeRequest
from app.models.document import DocumentVersion
from app.models.issue import Issue
from app.models.process_map import ProcessEdge, ProcessMapVersion, ProcessTask
from app.models.validation import ValidationCase
from app.pipeline.versioning import ChangeApplyError, apply_change
from app.schemas import (
    ChangeRequestDecisionIn,
    ChangeRequestOut,
    ChatRequest,
    ChatResponse,
    ChatSource,
    CitationOut,
    DocumentOut,
    EdgeOut,
    IssueFeedbackIn,
    IssueOut,
    ProcessMapOut,
    ProcessMapVersionOut,
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
            bpa_feedback=i.bpa_feedback, resolution_notes=i.resolution_notes,
        ))
    return out


@router.patch("/documents/{document_id}/issues/{issue_id}", response_model=IssueOut)
def update_issue_feedback(document_id: str, issue_id: str, body: IssueFeedbackIn, db: Session = Depends(get_db)):
    """BPA feedback loop for gaps/ambiguities (see FeedbackPanel): a BPA can
    leave a comment/proposed resolution and move status to pending_review, and
    a reviewer can separately resolve/defer with resolution_notes. This never
    touches the process map itself — resolving an issue is a record-keeping
    act, not an automatic edit (a genuine process-map change still has to go
    through the ChangeRequest approval path)."""
    issue = db.query(Issue).filter_by(id=issue_id, document_id=document_id).first()
    if issue is None:
        raise HTTPException(404, f"No issue {issue_id} for document {document_id}")

    if body.bpa_feedback is not None:
        issue.bpa_feedback = body.bpa_feedback
    if body.status is not None:
        valid = {"open", "pending_review", "resolved", "deferred"}
        if body.status not in valid:
            raise HTTPException(400, f"status must be one of {sorted(valid)}")
        issue.status = body.status
    if body.resolution_notes is not None:
        issue.resolution_notes = body.resolution_notes

    db.commit()
    db.refresh(issue)

    claims_by_id = {c.id: c for c in db.query(AtomicClaim).filter_by(document_id=document_id).all()}
    claim_ids = json.loads(issue.claim_refs or "[]")
    citations = [_citation_from_claim(claims_by_id[cid]) for cid in claim_ids if cid in claims_by_id]
    return IssueOut(
        id=issue.id, issue_type=issue.issue_type, title=issue.title, description=issue.description,
        status=issue.status, process_task_id=issue.process_task_id, claim_refs=citations,
        bpa_feedback=issue.bpa_feedback, resolution_notes=issue.resolution_notes,
    )


@router.get("/documents/{document_id}/process-map/versions", response_model=list[ProcessMapVersionOut])
def list_process_map_versions(document_id: str, db: Session = Depends(get_db)):
    versions = (
        db.query(ProcessMapVersion)
        .filter_by(document_id=document_id)
        .order_by(ProcessMapVersion.created_at.desc())
        .all()
    )
    if not versions:
        return []
    current_id = versions[0].id  # most recent = current, matches get_process_map's selection
    return [
        ProcessMapVersionOut(
            id=v.id, version_label=v.version_label, status=v.status,
            change_summary=v.change_summary, changed_by=v.changed_by,
            created_at=v.created_at, is_current=(v.id == current_id),
        )
        for v in versions
    ]


@router.get("/documents/{document_id}/change-requests", response_model=list[ChangeRequestOut])
def list_change_requests(document_id: str, db: Session = Depends(get_db)):
    crs = (
        db.query(ChangeRequest)
        .filter_by(document_id=document_id)
        .order_by(ChangeRequest.created_at.desc())
        .all()
    )
    return [
        ChangeRequestOut(
            id=c.id, document_id=c.document_id, source=c.source, request_text=c.request_text,
            change_type=c.change_type, proposed_change=json.loads(c.proposed_change or "{}"),
            rationale=c.rationale, status=c.status, decision_notes=c.decision_notes,
            resulting_process_map_id=c.resulting_process_map_id,
            created_at=c.created_at, decided_at=c.decided_at,
        )
        for c in crs
    ]


@router.post("/documents/{document_id}/change-requests/{cr_id}/approve", response_model=ChangeRequestOut)
def approve_change_request(document_id: str, cr_id: str, body: ChangeRequestDecisionIn, db: Session = Depends(get_db)):
    cr = db.query(ChangeRequest).filter_by(id=cr_id, document_id=document_id).first()
    if cr is None:
        raise HTTPException(404, f"No change request {cr_id} for document {document_id}")
    if cr.status != "pending":
        raise HTTPException(400, f"Change request is already {cr.status}, not pending")
    if cr.change_type == "unclear":
        raise HTTPException(400, "Cannot approve an 'unclear' change request — it has no structured edit to apply")

    base_pm = db.query(ProcessMapVersion).filter_by(id=cr.base_process_map_id).first()
    if base_pm is None:
        raise HTTPException(404, "Base process map version for this change request no longer exists")

    try:
        result = apply_change(
            db, document_id, base_pm, cr.change_type,
            json.loads(cr.proposed_change or "{}"), changed_by="bpa via chat feedback",
        )
    except ChangeApplyError as e:
        cr.status = "apply_failed"
        cr.decision_notes = str(e)
        db.commit()
        raise HTTPException(400, f"Could not apply this change: {e}")

    cr.status = "approved"
    cr.decision_notes = body.decision_notes
    cr.resulting_process_map_id = result.new_version.id
    cr.decided_at = dt.datetime.utcnow()
    result.new_version.change_request_id = cr.id
    db.commit()
    db.refresh(cr)

    return ChangeRequestOut(
        id=cr.id, document_id=cr.document_id, source=cr.source, request_text=cr.request_text,
        change_type=cr.change_type, proposed_change=json.loads(cr.proposed_change or "{}"),
        rationale=cr.rationale, status=cr.status, decision_notes=cr.decision_notes,
        resulting_process_map_id=cr.resulting_process_map_id,
        created_at=cr.created_at, decided_at=cr.decided_at,
    )


@router.post("/documents/{document_id}/change-requests/{cr_id}/reject", response_model=ChangeRequestOut)
def reject_change_request(document_id: str, cr_id: str, body: ChangeRequestDecisionIn, db: Session = Depends(get_db)):
    cr = db.query(ChangeRequest).filter_by(id=cr_id, document_id=document_id).first()
    if cr is None:
        raise HTTPException(404, f"No change request {cr_id} for document {document_id}")
    if cr.status != "pending":
        raise HTTPException(400, f"Change request is already {cr.status}, not pending")

    cr.status = "rejected"
    cr.decision_notes = body.decision_notes
    cr.decided_at = dt.datetime.utcnow()
    db.commit()
    db.refresh(cr)

    return ChangeRequestOut(
        id=cr.id, document_id=cr.document_id, source=cr.source, request_text=cr.request_text,
        change_type=cr.change_type, proposed_change=json.loads(cr.proposed_change or "{}"),
        rationale=cr.rationale, status=cr.status, decision_notes=cr.decision_notes,
        resulting_process_map_id=cr.resulting_process_map_id,
        created_at=cr.created_at, decided_at=cr.decided_at,
    )


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

    answer, mode, retrieved, change_request = handle_message(db, req.document_id, req.message)
    db.commit()

    sources: list[ChatSource] = []
    for r in retrieved:
        if not r.claims:
            sources.append(ChatSource(task_id=r.task.id, task_title=r.task.title, claim_id=None, subject=None, page=None, raw_quote=None))
        for c in r.claims:
            sources.append(ChatSource(
                task_id=r.task.id, task_title=r.task.title, claim_id=c.id,
                subject=c.subject, page=c.source_span.page, raw_quote=c.raw_quote,
            ))

    return ChatResponse(
        answer=answer, mode=mode, sources=sources,
        change_request_id=change_request.id if change_request else None,
    )
