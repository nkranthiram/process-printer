"""End-to-end seed test: runs the full pipeline (ingest → extract → synthesize →
issues) into a real database and checks the persisted graph is internally
consistent — this is the closest thing to an integration test for the whole
backend pipeline."""
import json

from app.seed import seed_aami
from app.models.document import DocumentVersion, SourceSpan
from app.models.claim import AtomicClaim
from app.models.process_map import ProcessMapVersion, ProcessTask, ProcessEdge
from app.models.issue import Issue
from app.models.validation import ValidationCase


def test_seed_aami_end_to_end(db_session):
    doc_id = seed_aami(db_session)

    doc = db_session.query(DocumentVersion).filter_by(id=doc_id).one()
    assert doc.status == "ready"
    assert doc.page_count == 76

    spans = db_session.query(SourceSpan).filter_by(document_id=doc_id).all()
    assert len(spans) > 300

    claims = db_session.query(AtomicClaim).filter_by(document_id=doc_id).all()
    assert len(claims) == 38
    for c in claims:
        assert c.source_span.document_id == doc_id  # FK actually resolves to a real, same-document span

    pm = db_session.query(ProcessMapVersion).filter_by(document_id=doc_id).one()
    tasks = db_session.query(ProcessTask).filter_by(process_map_id=pm.id).all()
    edges = db_session.query(ProcessEdge).filter_by(process_map_id=pm.id).all()
    assert len(tasks) == 11
    assert len(edges) == 14

    # Every edge's from/to task actually belongs to this same process map.
    task_ids = {t.id for t in tasks}
    for e in edges:
        assert e.from_task_id in task_ids
        assert e.to_task_id in task_ids

    # Every task's claim_refs resolve to real, persisted claim rows.
    claim_ids = {c.id for c in claims}
    for t in tasks:
        for cid in json.loads(t.claim_refs or "[]"):
            assert cid in claim_ids

    issues = db_session.query(Issue).filter_by(document_id=doc_id).all()
    assert len(issues) == 7
    for i in issues:
        if i.process_task_id:
            assert i.process_task_id in task_ids

    cases = db_session.query(ValidationCase).filter_by(process_map_id=pm.id).all()
    assert len(cases) == 5
    for c in cases:
        assert c.result in {"pass", "fail"}
        path = json.loads(c.traced_path)
        assert all(tid in task_ids for tid in path)


def test_seed_is_idempotent_on_rerun(db_session):
    """Re-seeding the same document must not accumulate duplicate rows — verifies
    the clear-existing-first logic in seed_aami."""
    doc_id_1 = seed_aami(db_session)
    doc_id_2 = seed_aami(db_session)

    docs = db_session.query(DocumentVersion).all()
    assert len(docs) == 1  # not 2 — the same content_hash replaced, not duplicated

    claims = db_session.query(AtomicClaim).all()
    assert len(claims) == 38  # not 76
