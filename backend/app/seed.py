"""Loads the AAMI PDS end-to-end through the real pipeline stages and persists the
result to the database — this is what the API layer serves. Re-runnable: clears any
prior data for this document's content_hash first (idempotent, not additive-forever).
"""
from __future__ import annotations

import json
from pathlib import Path

from app.database import SessionLocal, init_db
from app.models.document import DocumentVersion, SourceSpan
from app.models.claim import AtomicClaim
from app.models.process_map import ProcessMapVersion, ProcessTask, ProcessEdge
from app.models.issue import Issue
from app.models.validation import ValidationCase
from app.pipeline.ingestion import parse_pdf, content_hash as compute_hash
from app.pipeline.extraction import load_manual_seed, verify_citations
from app.pipeline.synthesis import load_process_map, validate_process_map
from app.pipeline.issues import load_manual_issues, validate_issues
from app.pipeline.validation import load_manual_validation_cases, validate_traced_paths
from app.pipeline.change_log import apply_change_log
from app.pipeline.agentic_workflow import load_manual_seed as load_agentic_workflow_seed, persist_agentic_workflow

AAMI_PDF = Path(__file__).parent.parent.parent.parent / "docs" / "aami-comprehensive-car-insurance-pds.pdf"


def _normalize(s: str) -> str:
    return s.lower().replace("ﬁ", "fi").replace("ﬂ", "fl").replace("’", "'").replace("‘", "'")


def seed_aami(db=None) -> str:
    """Returns the DocumentVersion id that was seeded."""
    owns_session = db is None
    db = db or SessionLocal()
    try:
        pdf_bytes = AAMI_PDF.read_bytes()
        chash = compute_hash(pdf_bytes)

        existing = db.query(DocumentVersion).filter_by(content_hash=chash).first()
        if existing:
            db.query(Issue).filter_by(document_id=existing.id).delete()
            for pm in db.query(ProcessMapVersion).filter_by(document_id=existing.id).all():
                db.delete(pm)
            db.query(AtomicClaim).filter_by(document_id=existing.id).delete()
            db.query(SourceSpan).filter_by(document_id=existing.id).delete()
            db.delete(existing)
            db.commit()

        parsed = parse_pdf(pdf_bytes, title_hint="AAMI Comprehensive Car Insurance PDS")

        doc = DocumentVersion(
            filename=AAMI_PDF.name,
            content_hash=chash,
            title=parsed.title,
            page_count=parsed.page_count,
            status="parsing",
        )
        db.add(doc)
        db.flush()

        span_rows = []
        for s in parsed.spans:
            row = SourceSpan(
                document_id=doc.id, page=s.page, section_path=s.section_path,
                bbox=s.bbox, text=s.text, order_index=s.order_index,
            )
            db.add(row)
            span_rows.append(row)
        db.flush()

        # --- claim extraction (manual-agent-pass-v1, see architecture.md) ---
        claim_drafts = load_manual_seed()
        citation_check = verify_citations(claim_drafts, parsed.spans)
        if not citation_check.all_verified:
            raise RuntimeError("Refusing to seed: citation verification failed:\n" + "\n".join(citation_check.failures))

        claim_id_by_subject: dict[str, str] = {}
        for cd in claim_drafts:
            # link to the first span on the cited page whose (normalized) text
            # contains the (normalized) raw_quote — same matching rule as the
            # verifier, so the FK is guaranteed resolvable.
            span_match = next(
                (r for r in span_rows if r.page == cd.page and _normalize(cd.raw_quote) in _normalize(r.text)),
                None,
            )
            if span_match is None:
                raise RuntimeError(f"No matching span for claim subject={cd.subject!r} page={cd.page}")
            claim = AtomicClaim(
                document_id=doc.id, source_span_id=span_match.id,
                claim_type=cd.claim_type, subject=cd.subject, predicate=cd.predicate,
                modality=cd.modality, statement=cd.statement, raw_quote=cd.raw_quote,
                conditions=json.dumps(cd.conditions), extraction_confidence=cd.extraction_confidence,
                extractor_version=cd.extractor_version, explicit=cd.explicit,
            )
            db.add(claim)
            db.flush()
            claim_id_by_subject[cd.subject] = claim.id

        # --- process map synthesis ---
        pm_draft = load_process_map()
        map_validation = validate_process_map(pm_draft, claim_drafts)
        if not map_validation.valid:
            raise RuntimeError("Refusing to seed: process map validation failed:\n" + "\n".join(map_validation.errors))

        pm = ProcessMapVersion(document_id=doc.id, version_label="v1", status="draft")
        db.add(pm)
        db.flush()

        task_id_by_local_id: dict[str, str] = {}
        for t in pm_draft.tasks:
            claim_ids = [claim_id_by_subject[s] for s in t.claim_refs]
            row = ProcessTask(
                process_map_id=pm.id, node_type=t.node_type, title=t.title,
                description=t.description, position_x=t.position[0] * 260,
                position_y=t.position[1] * 140, claim_refs=json.dumps(claim_ids),
            )
            db.add(row)
            db.flush()
            task_id_by_local_id[t.id] = row.id

        for e in pm_draft.edges:
            db.add(ProcessEdge(
                process_map_id=pm.id,
                from_task_id=task_id_by_local_id[e.from_id],
                to_task_id=task_id_by_local_id[e.to_id],
                condition_label=e.label,
            ))

        # --- issues ---
        issue_drafts = load_manual_issues()
        issue_validation = validate_issues(issue_drafts, pm_draft, claim_drafts)
        if not issue_validation.valid:
            raise RuntimeError("Refusing to seed: issue log validation failed:\n" + "\n".join(issue_validation.errors))

        for i in issue_drafts:
            db.add(Issue(
                document_id=doc.id,
                process_task_id=task_id_by_local_id.get(i.process_task_id) if i.process_task_id else None,
                issue_type=i.issue_type, title=i.title, description=i.description,
                claim_refs=json.dumps([claim_id_by_subject[s] for s in i.claim_refs]),
                status="open",
            ))

        # --- scenario validation cases ---
        case_drafts = load_manual_validation_cases()
        case_validation = validate_traced_paths(case_drafts, pm_draft)
        if not case_validation.valid:
            raise RuntimeError("Refusing to seed: validation case traces failed:\n" + "\n".join(case_validation.errors))

        for c in case_drafts:
            db.add(ValidationCase(
                process_map_id=pm.id,
                scenario_name=c.scenario_name,
                claim_description=c.claim_description,
                expected_outcome=c.expected_outcome,
                traced_path=json.dumps([task_id_by_local_id[t] for t in c.traced_path]),
                actual_outcome=c.actual_outcome,
                result=c.result,
                notes=c.notes,
            ))

        # --- replay the committed change log (backend/data/change_log/) ---
        # This is what makes approved BPA edits (v2, v3, ...) reproducible from
        # a clean clone/DB instead of only existing in someone's local, git-
        # ignored SQLite file. See app/pipeline/change_log.py for why titles
        # (not row ids) are the reference key, and docs/process-map-snapshots/
        # for how a live review session gets turned into a committed entry.
        db.flush()
        current_pm = apply_change_log(db, doc.id, pm)

        # --- agentic workflow spec (downstream, optional artifact -- see
        # skills/agentic-workflow-synthesis/SKILL.md) generated against the
        # CURRENT (post-replay) process map version, not v1, so its
        # source_task_title references match the map a BPA actually approved. ---
        db.flush()
        agentic_draft = load_agentic_workflow_seed()
        persist_agentic_workflow(db, doc.id, current_pm, agentic_draft, claim_id_by_subject)

        doc.status = "ready"
        db.commit()
        return doc.id
    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":
    init_db()
    doc_id = seed_aami()
    print(f"Seeded document {doc_id}")
