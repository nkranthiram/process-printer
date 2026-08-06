"""Tests for app/pipeline/review_session.py — the "Review & Apply Changes"
consolidation flow. Covers session reuse, heuristic (no-LLM-key) grounding
discipline, and the supersede mechanic."""
from __future__ import annotations

import json

import pytest

from app.models.document import DocumentVersion
from app.models.process_map import ProcessEdge, ProcessMapVersion, ProcessTask
from app.models.review_session import DraftChangeItem, ReviewSession
from app.pipeline.review_session import (
    consolidate_transcript,
    get_or_create_open_session,
)


def _seed_doc_and_map(db):
    doc = DocumentVersion(filename="x.pdf", content_hash="h", title="X", page_count=1, status="ready")
    db.add(doc)
    db.flush()
    pm = ProcessMapVersion(document_id=doc.id, version_label="v1", status="validated")
    db.add(pm)
    db.flush()
    t1 = ProcessTask(process_map_id=pm.id, node_type="input_required", title="Capture claim",
                      description="d1", position_x=0, position_y=0, claim_refs="[]")
    t2 = ProcessTask(process_map_id=pm.id, node_type="decision", title="Decide",
                      description="d2", position_x=0, position_y=1, claim_refs="[]")
    db.add_all([t1, t2])
    db.flush()
    db.add(ProcessEdge(process_map_id=pm.id, from_task_id=t1.id, to_task_id=t2.id, condition_label=None))
    db.commit()
    return doc, pm, (t1, t2)


def test_get_or_create_open_session_creates_pinned_to_current_head(db_session):
    doc, pm, _ = _seed_doc_and_map(db_session)
    session = get_or_create_open_session(db_session, doc.id)
    db_session.commit()

    assert session.document_id == doc.id
    assert session.base_process_map_id == pm.id
    assert session.status == "open"


def test_get_or_create_open_session_reuses_existing_open_session(db_session):
    doc, pm, _ = _seed_doc_and_map(db_session)
    s1 = get_or_create_open_session(db_session, doc.id)
    db_session.commit()
    s2 = get_or_create_open_session(db_session, doc.id)
    db_session.commit()

    assert s1.id == s2.id


def test_heuristic_consolidation_flags_feedback_as_needs_clarification_not_a_guess(db_session, monkeypatch):
    """RED-BEFORE-GREEN CONTROL: with no LLM key, the system must never
    fabricate a structured edit from free text — proven here by checking the
    resulting item is needs_clarification, not a guessed add/remove/modify."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    doc, pm, (t1, t2) = _seed_doc_and_map(db_session)
    session = get_or_create_open_session(db_session, doc.id)
    db_session.commit()

    transcript = [
        {"role": "user", "text": "Can we remove the decide step, it's redundant", "ref": "turn-1"},
        {"role": "assistant", "text": "Noted.", "ref": "turn-2"},
    ]
    items = consolidate_transcript(db_session, session, transcript)
    db_session.commit()

    assert len(items) == 1
    assert items[0].change_type == "needs_clarification"
    assert items[0].status == "needs_clarification"
    refs = json.loads(items[0].source_message_refs)
    assert refs == ["turn-1"]


def test_heuristic_consolidation_ignores_non_feedback_turns(db_session, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    doc, pm, (t1, t2) = _seed_doc_and_map(db_session)
    session = get_or_create_open_session(db_session, doc.id)
    db_session.commit()

    transcript = [
        {"role": "user", "text": "Why is the decide step at the end?", "ref": "turn-1"},
        {"role": "assistant", "text": "Because it's the terminal outcome.", "ref": "turn-2"},
    ]
    items = consolidate_transcript(db_session, session, transcript)
    db_session.commit()
    assert items == []


def test_session_status_becomes_reconciled_after_consolidation(db_session, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    doc, pm, (t1, t2) = _seed_doc_and_map(db_session)
    session = get_or_create_open_session(db_session, doc.id)
    db_session.commit()

    consolidate_transcript(db_session, session, [{"role": "user", "text": "add a step", "ref": "turn-1"}])
    db_session.commit()

    refreshed = db_session.query(ReviewSession).filter_by(id=session.id).first()
    assert refreshed.status == "reconciled"


def test_superseded_item_is_kept_not_deleted(db_session):
    """Directly exercises the supersede mechanic via _persist_consolidation's
    contract (through consolidate_transcript's persisted output), independent
    of whether an LLM or the heuristic path produced the supersedes_item_id —
    proves an old item is marked superseded, never removed, preserving the
    audit trail."""
    doc, pm, (t1, t2) = _seed_doc_and_map(db_session)
    session = get_or_create_open_session(db_session, doc.id)
    db_session.commit()

    from app.pipeline.review_session import _persist_consolidation

    first_pass = _persist_consolidation(db_session, session, [{
        "change_type": "remove_task", "payload": {"task_id": t2.id},
        "rationale": "seems redundant", "source_message_refs": ["turn-1"], "supersedes_item_id": None,
    }])
    db_session.commit()
    original_id = first_pass[0].id

    second_pass = _persist_consolidation(db_session, session, [{
        "change_type": "modify_task", "payload": {"task_id": t2.id, "description": "keep it but reword"},
        "rationale": "changed my mind", "source_message_refs": ["turn-2"], "supersedes_item_id": original_id,
    }])
    db_session.commit()

    original = db_session.query(DraftChangeItem).filter_by(id=original_id).first()
    assert original.status == "superseded"
    assert original.superseded_by_item_id == second_pass[0].id

    # active items exclude the superseded one
    assert original_id not in [i.id for i in second_pass]
