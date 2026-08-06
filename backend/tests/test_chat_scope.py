"""Tests for the chatbot's scope enforcement (app/chat.py). Per explicit user
instruction: this app never answers coverage questions, only explains the
process map or logs feedback as a change request. These tests exist because
that boundary is the single most safety-critical behavior in this feature —
getting it wrong means the chatbot silently becomes a coverage-advice tool."""
from __future__ import annotations

import json

import pytest

from app.chat import classify_intent, handle_message
from app.models.change_request import ChangeRequest
from app.models.document import DocumentVersion
from app.models.process_map import ProcessEdge, ProcessMapVersion, ProcessTask


COVERAGE_QUESTIONS = [
    "Is my windscreen damage covered?",
    "Am I covered if I hit a kangaroo?",
    "What's my excess for this claim?",
    "Will this claim be approved?",
    "Do I have cover for a stolen car?",
    "How much excess do I pay for a not-at-fault accident?",
]

CHANGE_REQUESTS = [
    "Can you add a step to verify the incident date?",
    "We should remove the additional covers step, it's redundant.",
    "Please change the description of the exclusions check step.",
    "This step shouldn't be here, remove it.",
]

EXPLAIN_QUESTIONS = [
    "Why is the exclusions check before the excess step?",
    "Why did you include the evidence check here?",
    "Explain what the classification step does.",
    "Walk me through the escalation step.",
]


@pytest.mark.parametrize("q", COVERAGE_QUESTIONS)
def test_coverage_questions_classified_out_of_scope(q):
    assert classify_intent(q) == "coverage_question"


@pytest.mark.parametrize("q", CHANGE_REQUESTS)
def test_change_requests_classified_correctly(q):
    assert classify_intent(q) == "change_request"


@pytest.mark.parametrize("q", EXPLAIN_QUESTIONS)
def test_explain_questions_classified_correctly(q):
    assert classify_intent(q) == "explain"


def _seed_doc_and_map(db):
    doc = DocumentVersion(filename="x.pdf", content_hash="h", title="X", page_count=1, status="ready")
    db.add(doc)
    db.flush()
    pm = ProcessMapVersion(document_id=doc.id, version_label="v1", status="validated")
    db.add(pm)
    db.flush()
    t1 = ProcessTask(process_map_id=pm.id, node_type="input_required", title="Capture claim",
                      description="Record the claim description", position_x=0, position_y=0, claim_refs="[]")
    t2 = ProcessTask(process_map_id=pm.id, node_type="decision", title="Decide",
                      description="Reach a decision", position_x=0, position_y=1, claim_refs="[]")
    db.add_all([t1, t2])
    db.flush()
    db.add(ProcessEdge(process_map_id=pm.id, from_task_id=t1.id, to_task_id=t2.id, condition_label=None))
    db.commit()
    return doc, pm, (t1, t2)


def test_coverage_question_never_reaches_retrieval_or_llm(db_session, monkeypatch):
    """RED-BEFORE-GREEN CONTROL: the coverage refusal must happen before any
    retrieval/LLM call — proven here by making retrieve() raise if it's ever
    called for a coverage question, not just by checking the returned mode."""
    doc, pm, _ = _seed_doc_and_map(db_session)

    import app.chat as chat_module

    def boom(*args, **kwargs):
        raise AssertionError("retrieve() must not be called for a coverage question")

    monkeypatch.setattr(chat_module, "retrieve", boom)

    answer, mode, retrieved, cr = handle_message(db_session, doc.id, "Is my windscreen covered?")
    assert mode == "out_of_scope"
    assert retrieved == []
    assert cr is None
    assert "doesn't answer coverage questions" in answer


def test_change_request_is_logged_pending_not_applied(db_session, monkeypatch):
    doc, pm, (t1, t2) = _seed_doc_and_map(db_session)

    import app.chat as chat_module
    monkeypatch.setattr(chat_module, "draft_change_request", lambda *a, **k: {
        "change_type": "remove_task", "payload": {"task_id": t2.id}, "rationale": "test",
    })

    answer, mode, retrieved, cr = handle_message(db_session, doc.id, "remove the decide step please")
    assert mode == "change_request_logged"
    assert cr is not None
    assert cr.status == "pending"
    assert cr.change_type == "remove_task"

    # Confirm it's a real committed row a reviewer can see, and the process map
    # itself is untouched (still 2 tasks, no new version created).
    db_session.commit()
    stored = db_session.query(ChangeRequest).filter_by(id=cr.id).first()
    assert stored is not None
    assert stored.status == "pending"
    task_count = db_session.query(ProcessTask).filter_by(process_map_id=pm.id).count()
    assert task_count == 2
