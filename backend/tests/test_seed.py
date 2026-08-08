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

    # As of the committed change-log replay (see app/pipeline/change_log.py),
    # seeding produces v1 (raw extraction) AND v2 (the real, already-approved
    # BPA edit replayed from backend/data/change_log/) -- not just one version.
    versions = db_session.query(ProcessMapVersion).filter_by(document_id=doc_id).order_by(
        ProcessMapVersion.created_at
    ).all()
    assert [v.version_label for v in versions] == ["v1", "v2"]
    v1, v2 = versions

    v1_tasks = db_session.query(ProcessTask).filter_by(process_map_id=v1.id).all()
    v1_edges = db_session.query(ProcessEdge).filter_by(process_map_id=v1.id).all()
    assert len(v1_tasks) == 11
    assert len(v1_edges) == 14

    # v2 = v1 minus "Check additional and optional covers" plus the identity
    # verification step -- the real, already-approved edit (see
    # backend/data/change_log/0001_*.json), not synthetic test data.
    pm = v2
    tasks = db_session.query(ProcessTask).filter_by(process_map_id=pm.id).all()
    edges = db_session.query(ProcessEdge).filter_by(process_map_id=pm.id).all()
    v2_titles = {t.title for t in tasks}
    assert "Check additional and optional covers" not in v2_titles
    assert "Verify policyholder identity against certificate of insurance" in v2_titles
    assert len(tasks) == 11  # one removed, one added

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

    # Issues are logged against the v1 tasks they were extracted alongside
    # (see seed.py) -- checked against v1's task ids, not v2's (v2's task rows
    # are freshly cloned with different ids by the versioning engine).
    v1_task_ids = {t.id for t in v1_tasks}
    issues = db_session.query(Issue).filter_by(document_id=doc_id).all()
    assert len(issues) == 7
    for i in issues:
        if i.process_task_id:
            assert i.process_task_id in v1_task_ids

    # v2 removed "Check additional and optional covers" (t9), so the 2 of the
    # original 5 scenarios that traced through it are correctly NOT carried
    # forward (see versioning.py's carry-forward logic) -- carrying them
    # forward with their old pass/fail verdict would misrepresent a scenario
    # that was never actually re-traced against the new structure.
    cases = db_session.query(ValidationCase).filter_by(process_map_id=pm.id).all()
    assert len(cases) == 3
    for c in cases:
        assert c.result in {"pass", "fail"}
        path = json.loads(c.traced_path)
        assert all(tid in task_ids for tid in path)
    assert v2.change_summary is not None and "dropped 2 validation case" in v2.change_summary


def test_seed_is_idempotent_on_rerun(db_session):
    """Re-seeding the same document must not accumulate duplicate rows — verifies
    the clear-existing-first logic in seed_aami."""
    doc_id_1 = seed_aami(db_session)
    doc_id_2 = seed_aami(db_session)

    docs = db_session.query(DocumentVersion).all()
    assert len(docs) == 1  # not 2 — the same content_hash replaced, not duplicated

    claims = db_session.query(AtomicClaim).all()
    assert len(claims) == 38  # not 76
