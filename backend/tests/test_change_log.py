"""Tests for app/pipeline/change_log.py -- proves committed change-log files
(backend/data/change_log/*.json) replay correctly on top of a freshly-seeded
v1 map, using TITLE references (not database row ids, which are regenerated
on every fresh seed). This is what makes an approved BPA edit reproducible
from a clean clone/DB instead of only existing in someone's local .db file."""
from __future__ import annotations

import json

import pytest

from app.models.document import DocumentVersion
from app.models.process_map import ProcessEdge, ProcessMapVersion, ProcessTask
from app.pipeline.change_log import ChangeLogError, apply_change_log, load_change_log


def _seed_linear_map(db):
    doc = DocumentVersion(filename="x.pdf", content_hash="h", title="X", page_count=1, status="ready")
    db.add(doc)
    db.flush()

    pm = ProcessMapVersion(document_id=doc.id, version_label="v1", status="validated")
    db.add(pm)
    db.flush()

    t1 = ProcessTask(process_map_id=pm.id, node_type="input_required", title="Capture claim",
                      description="d1", position_x=0, position_y=0, claim_refs="[]")
    t2 = ProcessTask(process_map_id=pm.id, node_type="eligibility_test", title="Check eligibility",
                      description="d2", position_x=0, position_y=1, claim_refs="[]")
    t3 = ProcessTask(process_map_id=pm.id, node_type="decision", title="Decide",
                      description="d3", position_x=0, position_y=2, claim_refs="[]")
    db.add_all([t1, t2, t3])
    db.flush()

    db.add(ProcessEdge(process_map_id=pm.id, from_task_id=t1.id, to_task_id=t2.id, condition_label=None))
    db.add(ProcessEdge(process_map_id=pm.id, from_task_id=t2.id, to_task_id=t3.id, condition_label=None))
    db.commit()
    return doc, pm


def test_empty_log_is_a_noop(db_session, tmp_path, monkeypatch):
    empty_dir = tmp_path / "change_log"
    empty_dir.mkdir()
    monkeypatch.setattr("app.pipeline.change_log.CHANGE_LOG_DIR", empty_dir)

    doc, pm = _seed_linear_map(db_session)
    result = apply_change_log(db_session, doc.id, pm)
    assert result.id == pm.id  # no new version created


def test_real_committed_log_file_replays_on_the_real_aami_seed_data(db_session):
    """Proves the actual committed 0001_*.json file (the real one seed.py
    uses) replays cleanly against the real AAMI v1 structure it was authored
    against -- built from the real synthesis draft (correct node types and
    branching edges), not a hand-typed linear stand-in."""
    from app.pipeline.synthesis import load_process_map

    pm_draft = load_process_map()

    doc = DocumentVersion(filename="aami.pdf", content_hash="h2", title="AAMI", page_count=1, status="ready")
    db_session.add(doc)
    db_session.flush()
    pm = ProcessMapVersion(document_id=doc.id, version_label="v1", status="draft")
    db_session.add(pm)
    db_session.flush()

    id_map = {}
    for i, t in enumerate(pm_draft.tasks):
        row = ProcessTask(process_map_id=pm.id, node_type=t.node_type, title=t.title,
                           description=t.description, position_x=0, position_y=i, claim_refs="[]")
        db_session.add(row)
        db_session.flush()
        id_map[t.id] = row.id
    for e in pm_draft.edges:
        db_session.add(ProcessEdge(process_map_id=pm.id, from_task_id=id_map[e.from_id],
                                    to_task_id=id_map[e.to_id], condition_label=e.label or None))
    db_session.commit()

    entries = load_change_log()
    assert len(entries) >= 1, "expected the real committed change-log file to be found"

    result = apply_change_log(db_session, doc.id, pm)

    assert result.id != pm.id
    assert result.version_label == "v2"
    new_titles = {t.title for t in db_session.query(ProcessTask).filter_by(process_map_id=result.id)}
    assert "Check additional and optional covers" not in new_titles
    assert "Verify policyholder identity against certificate of insurance" in new_titles
    # base version untouched
    base_titles = {t.title for t in db_session.query(ProcessTask).filter_by(process_map_id=pm.id)}
    assert "Check additional and optional covers" in base_titles


def test_unknown_title_reference_raises_change_log_error(db_session, tmp_path, monkeypatch):
    """RED-BEFORE-GREEN control: a change-log entry referencing a task title
    that doesn't exist must fail loudly, not silently no-op or apply to the
    wrong task."""
    doc, pm = _seed_linear_map(db_session)

    bad_dir = tmp_path / "change_log"
    bad_dir.mkdir()
    (bad_dir / "0001_bad.json").write_text(json.dumps({
        "changed_by": "test",
        "items": [{"change_type": "remove_task", "payload": {"task_title": "Does Not Exist"}}],
    }))
    monkeypatch.setattr("app.pipeline.change_log.CHANGE_LOG_DIR", bad_dir)

    with pytest.raises(ChangeLogError, match="Does Not Exist"):
        apply_change_log(db_session, doc.id, pm)


def test_multi_entry_log_applies_in_filename_order_and_can_reference_a_task_added_earlier(
    db_session, tmp_path, monkeypatch
):
    doc, pm = _seed_linear_map(db_session)

    log_dir = tmp_path / "change_log"
    log_dir.mkdir()
    (log_dir / "0001_add.json").write_text(json.dumps({
        "changed_by": "test",
        "items": [{
            "change_type": "add_task",
            "payload": {"after_task_title": "Capture claim", "node_type": "classification",
                        "title": "New Step", "description": "d"},
        }],
    }))
    (log_dir / "0002_modify_new_step.json").write_text(json.dumps({
        "changed_by": "test",
        "items": [{
            "change_type": "modify_task",
            "payload": {"task_title": "New Step", "description": "updated description"},
        }],
    }))
    monkeypatch.setattr("app.pipeline.change_log.CHANGE_LOG_DIR", log_dir)

    final = apply_change_log(db_session, doc.id, pm)
    task = db_session.query(ProcessTask).filter_by(process_map_id=final.id, title="New Step").first()
    assert task is not None
    assert task.description == "updated description"
    # two entries -> two new versions (v2, v3), matching apply_change_set's
    # "one entry = one version" semantics
    assert final.version_label == "v3"
