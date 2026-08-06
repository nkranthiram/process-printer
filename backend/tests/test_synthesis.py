"""Tests for process-map-synthesis: the AAMI coverage-determination map must pass
all structural validation, and each validator must be provably able to fail."""
import copy

from app.pipeline.extraction import load_manual_seed
from app.pipeline.synthesis import (
    load_process_map,
    validate_process_map,
    validate_dag_structure,
    validate_claim_refs,
    validate_node_types,
    ProcessMapDraft,
    TaskDraft,
    EdgeDraft,
)


def test_aami_process_map_is_fully_valid():
    process_map = load_process_map()
    claims = load_manual_seed()
    report = validate_process_map(process_map, claims)
    if not report.valid:
        raise AssertionError("Process map validation failed:\n" + "\n".join(report.errors))
    assert report.valid


def test_task_count_is_in_readable_range():
    """Per the skill's contract: task-level, not clause-level — should stay
    roughly 10-20 nodes for a single process."""
    process_map = load_process_map()
    assert 8 <= len(process_map.tasks) <= 20, (
        f"got {len(process_map.tasks)} tasks — outside the 'a handler can hold this "
        f"in their head' range the skill specifies"
    )


def test_every_content_task_has_claim_refs_or_is_structural():
    """Every task should either cite claims, or be a structural/decision/escalation
    node with no content of its own to cite (input_required, decision, human_review)."""
    process_map = load_process_map()
    structural_types = {"input_required", "decision", "human_review"}
    for task in process_map.tasks:
        if task.node_type not in structural_types:
            assert task.claim_refs, f"content task {task.id!r} ({task.title!r}) has no claim_refs"


def _sample_map():
    return ProcessMapDraft(
        process_name="test",
        tasks=[
            TaskDraft("a", "input_required", "A", "desc", [], (0, 0)),
            TaskDraft("b", "decision", "B", "desc", [], (0, 1)),
        ],
        edges=[EdgeDraft("a", "b", "Always")],
    )


def test_validate_dag_structure_catches_a_cycle():
    m = _sample_map()
    m.tasks.append(TaskDraft("c", "eligibility_test", "C", "desc", [], (0, 2)))
    m.edges = [EdgeDraft("a", "c", "x"), EdgeDraft("c", "a", "y"), EdgeDraft("c", "b", "z")]
    # now 'a' has an incoming edge too, so no unique root — but more importantly, a cycle a->c->a
    report = validate_dag_structure(m)
    assert not report.valid
    assert any("cycle" in e for e in report.errors)


def test_validate_dag_structure_catches_non_terminal_leaf():
    m = _sample_map()
    m.tasks[1] = TaskDraft("b", "eligibility_test", "B", "desc", [], (0, 1))  # not a terminal type, and it's a leaf
    report = validate_dag_structure(m)
    assert not report.valid
    assert any("not a terminal type" in e for e in report.errors)


def test_validate_claim_refs_catches_dangling_reference():
    m = _sample_map()
    m.tasks[0].claim_refs = ["subject_that_does_not_exist"]
    claims = load_manual_seed()
    report = validate_claim_refs(m, claims)
    assert not report.valid
    assert "subject_that_does_not_exist" in report.errors[0]


def test_validate_node_types_catches_invalid_type():
    m = _sample_map()
    m.tasks[0].node_type = "not_a_real_type"
    report = validate_node_types(m)
    assert not report.valid
