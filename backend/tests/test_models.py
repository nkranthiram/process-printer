"""Round-trip tests for the core data model.

Covers: creating a document + span + claim + process map (task/edge) + issue +
validation case, and reading them back via relationships. This is the schema every
later pipeline stage depends on — if this is wrong, everything built on it is wrong.
"""
import json

from app.models.document import DocumentVersion, SourceSpan
from app.models.claim import AtomicClaim
from app.models.process_map import ProcessMapVersion, ProcessTask, ProcessEdge
from app.models.issue import Issue
from app.models.validation import ValidationCase


def test_document_and_span_round_trip(db_session):
    doc = DocumentVersion(
        filename="aami-comprehensive-car-insurance-pds.pdf",
        content_hash="abc123",
        title="AAMI Comprehensive Car Insurance PDS",
        page_count=100,
        status="ready",
    )
    db_session.add(doc)
    db_session.commit()

    span = SourceSpan(
        document_id=doc.id,
        page=42,
        section_path="Section 4 > Windscreen and window glass",
        text="We will pay to repair or replace glass...",
        order_index=0,
    )
    db_session.add(span)
    db_session.commit()

    fetched = db_session.query(DocumentVersion).filter_by(id=doc.id).one()
    assert fetched.title == "AAMI Comprehensive Car Insurance PDS"
    assert len(fetched.spans) == 1
    assert fetched.spans[0].page == 42


def test_claim_links_to_span_and_document(db_session):
    doc = DocumentVersion(filename="f.pdf", content_hash="h1", title="T", status="ready")
    db_session.add(doc)
    db_session.commit()

    span = SourceSpan(document_id=doc.id, page=1, text="raw text", order_index=0)
    db_session.add(span)
    db_session.commit()

    claim = AtomicClaim(
        document_id=doc.id,
        source_span_id=span.id,
        claim_type="exclusion",
        subject="windscreen_claim",
        predicate="excluded_if_pre_existing_damage",
        modality="excludes",
        statement="Pre-existing chips are not covered.",
        raw_quote="We won't pay for damage that existed before your policy started.",
        conditions=json.dumps(["pre_existing_damage == true"]),
        extraction_confidence=0.9,
        extractor_version="manual-agent-pass-v1",
    )
    db_session.add(claim)
    db_session.commit()

    fetched = db_session.query(AtomicClaim).filter_by(id=claim.id).one()
    assert fetched.source_span.text == "raw text"
    assert json.loads(fetched.conditions) == ["pre_existing_damage == true"]


def test_process_map_tasks_and_edges(db_session):
    doc = DocumentVersion(filename="f.pdf", content_hash="h2", title="T", status="ready")
    db_session.add(doc)
    db_session.commit()

    pm = ProcessMapVersion(document_id=doc.id, version_label="v0-draft", status="draft")
    db_session.add(pm)
    db_session.commit()

    t1 = ProcessTask(process_map_id=pm.id, node_type="input_required", title="Capture claim description", description="...")
    t2 = ProcessTask(process_map_id=pm.id, node_type="decision", title="Determine coverage", description="...")
    db_session.add_all([t1, t2])
    db_session.commit()

    edge = ProcessEdge(process_map_id=pm.id, from_task_id=t1.id, to_task_id=t2.id, condition_label="always")
    db_session.add(edge)
    db_session.commit()

    fetched_pm = db_session.query(ProcessMapVersion).filter_by(id=pm.id).one()
    assert len(fetched_pm.tasks) == 2
    assert len(fetched_pm.edges) == 1
    assert fetched_pm.edges[0].from_task_id == t1.id
    assert fetched_pm.edges[0].to_task_id == t2.id


def test_issue_and_validation_case(db_session):
    doc = DocumentVersion(filename="f.pdf", content_hash="h3", title="T", status="ready")
    db_session.add(doc)
    db_session.commit()

    issue = Issue(
        document_id=doc.id,
        issue_type="gap",
        title="No stated time limit for lodging a claim",
        description="The PDS doesn't specify a submission deadline for this claim type.",
        status="open",
    )
    db_session.add(issue)
    db_session.commit()

    fetched_issue = db_session.query(Issue).filter_by(id=issue.id).one()
    assert fetched_issue.status == "open"

    pm = ProcessMapVersion(document_id=doc.id, version_label="v0-draft")
    db_session.add(pm)
    db_session.commit()

    vc = ValidationCase(
        process_map_id=pm.id,
        scenario_name="Windscreen chip, comprehensive cover, no excess waiver",
        claim_description="Customer's windscreen was chipped by a stone on the highway.",
        expected_outcome="Covered under Windscreen and Window Glass benefit.",
        traced_path=json.dumps(["task-1", "task-2"]),
        actual_outcome="Covered under Windscreen and Window Glass benefit.",
        result="pass",
    )
    db_session.add(vc)
    db_session.commit()

    fetched_vc = db_session.query(ValidationCase).filter_by(id=vc.id).one()
    assert fetched_vc.result == "pass"
    assert json.loads(fetched_vc.traced_path) == ["task-1", "task-2"]
