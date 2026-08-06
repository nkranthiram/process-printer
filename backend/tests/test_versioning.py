"""Tests for app/pipeline/versioning.py — proves changes clone into a brand-new
ProcessMapVersion, never mutate the base version, and reject changes that would
break DAG structure. See skills/process-printer/SKILL.md's non-negotiable:
never auto-resolve/silently corrupt the map."""
from __future__ import annotations

import json

import pytest

from app.database import Base
from app.models.document import DocumentVersion
from app.models.process_map import ProcessEdge, ProcessMapVersion, ProcessTask
from app.pipeline.versioning import ChangeApplyError, apply_change


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
    return doc, pm, (t1, t2, t3)


def test_base_version_is_never_mutated(db_session):
    """RED-BEFORE-GREEN CONTROL: prove the base version's own task count/titles
    are provably unchanged after an apply — this is the property most likely to
    silently break if a future edit accidentally updates rows in place instead
    of cloning."""
    doc, pm, (t1, t2, t3) = _seed_linear_map(db_session)
    base_task_count_before = db_session.query(ProcessTask).filter_by(process_map_id=pm.id).count()
    base_titles_before = sorted(t.title for t in db_session.query(ProcessTask).filter_by(process_map_id=pm.id))

    apply_change(
        db_session, doc.id, pm,
        change_type="add_task",
        payload={"after_task_id": t1.id, "node_type": "classification",
                  "title": "New middle step", "description": "desc"},
        changed_by="test",
    )
    db_session.commit()

    base_task_count_after = db_session.query(ProcessTask).filter_by(process_map_id=pm.id).count()
    base_titles_after = sorted(t.title for t in db_session.query(ProcessTask).filter_by(process_map_id=pm.id))
    assert base_task_count_after == base_task_count_before == 3
    assert base_titles_after == base_titles_before


def test_add_task_creates_new_version_with_inserted_node(db_session):
    doc, pm, (t1, t2, t3) = _seed_linear_map(db_session)

    result = apply_change(
        db_session, doc.id, pm,
        change_type="add_task",
        payload={"after_task_id": t1.id, "node_type": "classification",
                  "title": "New middle step", "description": "desc"},
        changed_by="test",
    )
    db_session.commit()

    assert result.new_version.id != pm.id
    assert result.new_version.version_label == "v2"

    new_tasks = db_session.query(ProcessTask).filter_by(process_map_id=result.new_version.id).all()
    assert len(new_tasks) == 4
    titles = {t.title for t in new_tasks}
    assert "New middle step" in titles

    new_edges = db_session.query(ProcessEdge).filter_by(process_map_id=result.new_version.id).all()
    assert len(new_edges) == 3  # t1->new, new->t2, t2->t3

    # the new task must genuinely sit BETWEEN t1 and t2, not just be present
    new_task = next(t for t in new_tasks if t.title == "New middle step")
    edge_in = [e for e in new_edges if e.to_task_id == new_task.id]
    edge_out = [e for e in new_edges if e.from_task_id == new_task.id]
    assert len(edge_in) == 1 and len(edge_out) == 1


def test_remove_task_reconnects_predecessor_to_successor(db_session):
    doc, pm, (t1, t2, t3) = _seed_linear_map(db_session)

    result = apply_change(
        db_session, doc.id, pm,
        change_type="remove_task",
        payload={"task_id": t2.id},
        changed_by="test",
    )
    db_session.commit()

    new_tasks = db_session.query(ProcessTask).filter_by(process_map_id=result.new_version.id).all()
    assert len(new_tasks) == 2
    assert {t.title for t in new_tasks} == {"Capture claim", "Decide"}

    new_edges = db_session.query(ProcessEdge).filter_by(process_map_id=result.new_version.id).all()
    assert len(new_edges) == 1  # t1 now points directly at t3
    t1_new = next(t for t in new_tasks if t.title == "Capture claim")
    t3_new = next(t for t in new_tasks if t.title == "Decide")
    assert new_edges[0].from_task_id == t1_new.id
    assert new_edges[0].to_task_id == t3_new.id


def test_modify_task_updates_only_targeted_fields(db_session):
    doc, pm, (t1, t2, t3) = _seed_linear_map(db_session)

    result = apply_change(
        db_session, doc.id, pm,
        change_type="modify_task",
        payload={"task_id": t2.id, "description": "Updated description text"},
        changed_by="test",
    )
    db_session.commit()

    new_tasks = {t.title: t for t in db_session.query(ProcessTask).filter_by(process_map_id=result.new_version.id)}
    assert new_tasks["Check eligibility"].description == "Updated description text"


def test_remove_task_that_would_break_dag_is_rejected(db_session):
    """RED-BEFORE-GREEN: removing the only decision (terminal) node with no
    reconnection would leave a dangling non-terminal leaf — the same structural
    validator used at build time must catch this, proving it's genuinely wired
    in here and not just imported unused."""
    doc, pm, (t1, t2, t3) = _seed_linear_map(db_session)

    with pytest.raises(ChangeApplyError, match="terminal"):
        apply_change(
            db_session, doc.id, pm,
            change_type="remove_task",
            payload={"task_id": t3.id},  # the only decision/terminal node
            changed_by="test",
        )


def test_unknown_task_id_is_rejected(db_session):
    doc, pm, (t1, t2, t3) = _seed_linear_map(db_session)
    with pytest.raises(ChangeApplyError, match="does not exist"):
        apply_change(
            db_session, doc.id, pm,
            change_type="modify_task",
            payload={"task_id": "not-a-real-id", "title": "x"},
            changed_by="test",
        )
