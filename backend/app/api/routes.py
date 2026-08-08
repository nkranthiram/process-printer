from __future__ import annotations

import datetime as dt
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.chat import handle_message
from app.database import get_db
from app.models.claim import AtomicClaim
from app.models.agentic_workflow import AgenticWorkflowEdge, AgenticWorkflowNode, AgenticWorkflowVersion
from app.models.change_request import ChangeRequest
from app.models.document import DocumentVersion
from app.models.issue import Issue
from app.models.process_map import ProcessEdge, ProcessMapVersion, ProcessTask
from app.models.review_session import DraftChangeItem, ReviewSession
from app.models.validation import ValidationCase
from app.pipeline.review_session import consolidate_transcript, get_or_create_open_session
from app.pipeline.versioning import ChangeApplyError, ChangeSetItemInput, apply_change, apply_change_set
from app.schemas import (
    AgenticWorkflowEdgeOut,
    AgenticWorkflowNodeOut,
    AgenticWorkflowOut,
    ChangeRequestDecisionIn,
    ChangeRequestOut,
    ChatRequest,
    ChatResponse,
    ChatSource,
    CitationOut,
    ConfirmResultOut,
    ConsolidateRequestIn,
    DocumentOut,
    DraftChangeItemOut,
    DraftItemUpdateIn,
    EdgeOut,
    IssueFeedbackIn,
    IssueOut,
    ProcessMapOut,
    ProcessMapVersionOut,
    ReviewSessionOut,
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


@router.get("/documents/{document_id}/agentic-workflow", response_model=AgenticWorkflowOut)
def get_agentic_workflow(document_id: str, db: Session = Depends(get_db)):
    """Returns the agentic workflow spec generated from the CURRENT process
    map version (see skills/agentic-workflow-synthesis/SKILL.md). 404 if none
    has been generated yet for this document -- this is a downstream, optional
    artifact, not guaranteed to exist just because a process map does."""
    workflow = (
        db.query(AgenticWorkflowVersion)
        .filter_by(document_id=document_id)
        .order_by(AgenticWorkflowVersion.created_at.desc())
        .first()
    )
    if workflow is None:
        raise HTTPException(404, f"No agentic workflow generated yet for document {document_id}")

    claims_by_id = {c.id: c for c in db.query(AtomicClaim).filter_by(document_id=document_id).all()}

    nodes = db.query(AgenticWorkflowNode).filter_by(workflow_id=workflow.id).all()
    node_outs = []
    for n in nodes:
        claim_ids = json.loads(n.claim_refs or "[]")
        citations = [_citation_from_claim(claims_by_id[cid]) for cid in claim_ids if cid in claims_by_id]
        node_outs.append(AgenticWorkflowNodeOut(
            id=n.id, node_kind=n.node_kind, title=n.title, goal=n.goal,
            source_task_title=n.source_task_title, spec=json.loads(n.spec_json), citations=citations,
        ))

    edges = db.query(AgenticWorkflowEdge).filter_by(workflow_id=workflow.id).all()
    edge_outs = [
        AgenticWorkflowEdgeOut(id=e.id, from_node_id=e.from_node_id, to_node_id=e.to_node_id,
                                condition_label=e.condition_label)
        for e in edges
    ]

    return AgenticWorkflowOut(
        id=workflow.id, document_id=workflow.document_id,
        process_map_version_id=workflow.process_map_version_id,
        process_map_version_label=workflow.process_map_version_label,
        generator_version=workflow.generator_version, status=workflow.status,
        nodes=node_outs, edges=edge_outs,
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


def _draft_item_out(item: DraftChangeItem) -> DraftChangeItemOut:
    return DraftChangeItemOut(
        id=item.id, session_id=item.session_id, change_type=item.change_type,
        proposed_change=json.loads(item.proposed_change or "{}"), rationale=item.rationale,
        source_message_refs=json.loads(item.source_message_refs or "[]"), status=item.status,
        superseded_by_item_id=item.superseded_by_item_id, human_override=item.human_override,
        created_at=item.created_at, updated_at=item.updated_at,
    )


def _review_session_out(db: Session, session: ReviewSession) -> ReviewSessionOut:
    items = db.query(DraftChangeItem).filter_by(session_id=session.id).order_by(DraftChangeItem.created_at).all()
    return ReviewSessionOut(
        id=session.id, document_id=session.document_id, base_process_map_id=session.base_process_map_id,
        status=session.status, created_at=session.created_at, confirmed_at=session.confirmed_at,
        resulting_process_map_id=session.resulting_process_map_id,
        items=[_draft_item_out(i) for i in items],
    )


@router.get("/documents/{document_id}/review-sessions/current", response_model=ReviewSessionOut | None)
def get_current_review_session(document_id: str, db: Session = Depends(get_db)):
    session = (
        db.query(ReviewSession)
        .filter_by(document_id=document_id)
        .filter(ReviewSession.status.in_(["open", "reconciled"]))
        .order_by(ReviewSession.created_at.desc())
        .first()
    )
    if session is None:
        return None
    return _review_session_out(db, session)


@router.post("/documents/{document_id}/review-sessions/consolidate", response_model=ReviewSessionOut)
def consolidate_review_session(document_id: str, body: ConsolidateRequestIn, db: Session = Depends(get_db)):
    """The 'Review & Apply Changes' button. Runs the reconciliation pass over
    the supplied transcript (see app/pipeline/review_session.py) and returns
    the consolidated, still-editable draft item list for the BPA to confirm.
    Applies NOTHING to the process map — that only happens via /confirm."""
    doc = db.query(DocumentVersion).filter_by(id=document_id).first()
    if doc is None:
        raise HTTPException(404, f"Unknown document_id {document_id}")

    try:
        session = get_or_create_open_session(db, document_id)
    except ValueError as e:
        raise HTTPException(404, str(e))

    transcript = [t.model_dump() for t in body.transcript]
    consolidate_transcript(db, session, transcript)
    db.commit()
    db.refresh(session)
    return _review_session_out(db, session)


@router.patch("/documents/{document_id}/review-sessions/{session_id}/items/{item_id}", response_model=DraftChangeItemOut)
def update_draft_item(document_id: str, session_id: str, item_id: str, body: DraftItemUpdateIn, db: Session = Depends(get_db)):
    """The item-level dispute loop: approve / reject / edit wording / mark
    needs_clarification. A BPA edit to change_type/proposed_change/rationale
    is tagged human_override=True — distinct from LLM-derived content, per the
    'review-gaming' pitfall named in the design debate (a freely-editable
    confirm list must not silently launder ungrounded human edits as if they
    were still transcript-derived)."""
    item = (
        db.query(DraftChangeItem)
        .join(ReviewSession)
        .filter(DraftChangeItem.id == item_id, DraftChangeItem.session_id == session_id, ReviewSession.document_id == document_id)
        .first()
    )
    if item is None:
        raise HTTPException(404, f"No draft item {item_id} in session {session_id} for document {document_id}")

    edited_content = False
    if body.status is not None:
        valid = {"draft", "approved", "rejected", "needs_clarification"}
        if body.status not in valid:
            raise HTTPException(400, f"status must be one of {sorted(valid)}")
        item.status = body.status
    if body.change_type is not None:
        item.change_type = body.change_type
        edited_content = True
    if body.proposed_change is not None:
        item.proposed_change = json.dumps(body.proposed_change)
        edited_content = True
    if body.rationale is not None:
        item.rationale = body.rationale
        edited_content = True
    if edited_content:
        item.human_override = True

    db.commit()
    db.refresh(item)
    return _draft_item_out(item)


@router.post("/documents/{document_id}/review-sessions/{session_id}/confirm", response_model=ConfirmResultOut)
def confirm_review_session(document_id: str, session_id: str, db: Session = Depends(get_db)):
    """Applies every item with status=approved as ONE new process-map
    version. Nothing else (draft/rejected/needs_clarification items) is
    applied. If HEAD has moved since the session's base version was pinned
    (e.g. another change was approved via the per-message ChangeRequest path
    in the meantime), refuses and asks for a re-consolidation against current
    HEAD rather than applying against a stale base."""
    session = db.query(ReviewSession).filter_by(id=session_id, document_id=document_id).first()
    if session is None:
        raise HTTPException(404, f"No review session {session_id} for document {document_id}")
    if session.status not in ("open", "reconciled"):
        raise HTTPException(400, f"Session is already {session.status}")

    current_head = (
        db.query(ProcessMapVersion)
        .filter_by(document_id=document_id)
        .order_by(ProcessMapVersion.created_at.desc())
        .first()
    )
    if current_head is None or current_head.id != session.base_process_map_id:
        raise HTTPException(
            409,
            "The process map has changed since this review session started — "
            "re-run 'Review & Apply Changes' to consolidate against the current version before confirming.",
        )

    approved = (
        db.query(DraftChangeItem)
        .filter_by(session_id=session.id, status="approved")
        .order_by(DraftChangeItem.created_at)
        .all()
    )
    if not approved:
        raise HTTPException(400, "No approved items to apply — approve at least one item first")

    items_input = [
        ChangeSetItemInput(item_id=it.id, change_type=it.change_type, payload=json.loads(it.proposed_change or "{}"))
        for it in approved
    ]

    try:
        result = apply_change_set(db, document_id, current_head, items_input, changed_by="bpa via review session")
    except ChangeApplyError as e:
        failing = db.query(DraftChangeItem).filter_by(id=e.item_id).first() if e.item_id else None
        if failing:
            failing.status = "apply_failed"
            db.commit()
        return ConfirmResultOut(success=False, failed_item_id=e.item_id, error=str(e))

    for it in approved:
        it.status = "applied"
    session.status = "confirmed"
    session.confirmed_at = dt.datetime.utcnow()
    session.resulting_process_map_id = result.new_version.id
    result.new_version.change_request_id = session.id
    db.commit()
    db.refresh(result.new_version)

    versions = (
        db.query(ProcessMapVersion)
        .filter_by(document_id=document_id)
        .order_by(ProcessMapVersion.created_at.desc())
        .all()
    )
    current_id = versions[0].id if versions else None

    return ConfirmResultOut(
        success=True,
        new_version=ProcessMapVersionOut(
            id=result.new_version.id, version_label=result.new_version.version_label,
            status=result.new_version.status, change_summary=result.new_version.change_summary,
            changed_by=result.new_version.changed_by, created_at=result.new_version.created_at,
            is_current=(result.new_version.id == current_id),
        ),
        change_summaries=result.change_summaries,
    )


@router.post("/documents/{document_id}/review-sessions/{session_id}/discard", response_model=ReviewSessionOut)
def discard_review_session(document_id: str, session_id: str, db: Session = Depends(get_db)):
    session = db.query(ReviewSession).filter_by(id=session_id, document_id=document_id).first()
    if session is None:
        raise HTTPException(404, f"No review session {session_id} for document {document_id}")
    session.status = "discarded"
    db.commit()
    db.refresh(session)
    return _review_session_out(db, session)
